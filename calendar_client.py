"""Google Calendar FreeBusy client (OAuth user auth) and availability union logic."""
from __future__ import annotations

import datetime as dt
import os
from zoneinfo import ZoneInfo

import uuid

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

JST = ZoneInfo("Asia/Tokyo")
# calendar.events は free/busy 読み取り + イベント作成の両方に対応
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

Interval = tuple[dt.datetime, dt.datetime]


def get_service(client_secrets_file: str, token_file: str):
    """ローカル用: ファイルからトークン読込、無ければOAuthフロー起動。"""
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_service_from_token_info(token_info: dict):
    """デプロイ用: dictとして渡されたトークンを使う。期限切れなら自動refresh。"""
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError(
                "Token invalid and cannot be refreshed. Re-authorize locally and update secrets."
            )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def fetch_busy(
    service,
    emails: list[str],
    time_min: dt.datetime,
    time_max: dt.datetime,
) -> dict[str, list[Interval]]:
    body = {
        "timeMin": time_min.isoformat(),
        "timeMax": time_max.isoformat(),
        "timeZone": "Asia/Tokyo",
        "items": [{"id": e} for e in emails],
    }
    result = service.freebusy().query(body=body).execute()
    out: dict[str, list[Interval]] = {}
    for email, info in result.get("calendars", {}).items():
        if info.get("errors"):
            raise RuntimeError(f"{email}: {info['errors']}")
        periods: list[Interval] = []
        for p in info.get("busy", []):
            s = dt.datetime.fromisoformat(p["start"].replace("Z", "+00:00")).astimezone(JST)
            e = dt.datetime.fromisoformat(p["end"].replace("Z", "+00:00")).astimezone(JST)
            periods.append((s, e))
        out[email] = periods
    return out


def free_within_window(
    busy: list[Interval], window_start: dt.datetime, window_end: dt.datetime
) -> list[Interval]:
    """Subtract busy intervals from [window_start, window_end]."""
    clipped: list[Interval] = []
    for s, e in busy:
        if e <= window_start or s >= window_end:
            continue
        clipped.append((max(s, window_start), min(e, window_end)))
    clipped.sort()

    merged: list[Interval] = []
    for s, e in clipped:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    free: list[Interval] = []
    cursor = window_start
    for s, e in merged:
        if cursor < s:
            free.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < window_end:
        free.append((cursor, window_end))
    return free


def union(intervals: list[Interval]) -> list[Interval]:
    if not intervals:
        return []
    sorted_ints = sorted(intervals)
    merged = [sorted_ints[0]]
    for s, e in sorted_ints[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    return merged


def filter_by_min_duration(
    intervals: list[Interval], min_minutes: int
) -> list[Interval]:
    min_td = dt.timedelta(minutes=min_minutes)
    return [(s, e) for s, e in intervals if (e - s) >= min_td]


def compute_daily_union(
    service,
    emails: list[str],
    start_date: dt.date,
    end_date: dt.date,
    work_start_hour: int,
    work_end_hour: int,
    min_slot_minutes: dict[str, int] | None = None,
) -> list[tuple[dt.date, list[Interval], dict[str, list[Interval]]]]:
    """[start_date, end_date]（両端含む）の各日について
    (date, union_intervals, per_person_filtered_intervals) を返す。"""
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")
    min_slot_minutes = min_slot_minutes or {}

    target_dates: list[dt.date] = []
    cur = start_date
    while cur <= end_date:
        target_dates.append(cur)
        cur += dt.timedelta(days=1)

    time_min = dt.datetime.combine(start_date, dt.time(work_start_hour, 0), tzinfo=JST)
    time_max = dt.datetime.combine(end_date, dt.time(work_end_hour, 0), tzinfo=JST)

    busy_map = fetch_busy(service, emails, time_min, time_max)

    results = []
    for d in target_dates:
        day_start = dt.datetime.combine(d, dt.time(work_start_hour, 0), tzinfo=JST)
        day_end = dt.datetime.combine(d, dt.time(work_end_hour, 0), tzinfo=JST)
        per_person: dict[str, list[Interval]] = {}
        all_free: list[Interval] = []
        for email in emails:
            free = free_within_window(busy_map.get(email, []), day_start, day_end)
            filtered = filter_by_min_duration(free, min_slot_minutes.get(email, 0))
            per_person[email] = filtered
            all_free.extend(filtered)
        results.append((d, union(all_free), per_person))
    return results


_WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def _fmt_intervals(intervals: list[Interval]) -> str:
    if not intervals:
        return "なし"
    return " / ".join(
        f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}" for s, e in intervals
    )


def _date_label(d: dt.date) -> str:
    return f"{d.month}/{d.day}({_WEEKDAYS[d.weekday()]})"


def format_union_only(
    results: list[tuple[dt.date, list[Interval], dict[str, list[Interval]]]],
) -> str:
    """DM貼り付け用の合算テキスト（短い）。"""
    lines: list[str] = []
    for d, intervals, _ in results:
        time_str = "空きなし" if not intervals else _fmt_intervals(intervals)
        lines.append(f"【{_date_label(d)}】{time_str}")
    return "\n".join(lines)


def generate_candidate_slots(
    busy: list[Interval],
    start_date: dt.date,
    end_date: dt.date,
    work_start_hour: int,
    work_end_hour: int,
    duration_minutes: int,
    step_minutes: int = 30,
    weekdays: list[int] | None = None,
    now: dt.datetime | None = None,
) -> list[Interval]:
    """指定期間内で、staffが空いてる連続時間の中から duration_minutes 入る候補枠を列挙。
    step_minutes 刻みで開始時刻を生成し、そのまま duration_minutes 取れる枠だけ返す。
    weekdays は 0=月 6=日 のリスト（Noneなら全曜日）。
    now を指定すると、それ以降の枠のみ返す（過去は除外）。"""
    if weekdays is None:
        weekdays = list(range(7))
    now = now or dt.datetime.now(JST)
    duration = dt.timedelta(minutes=duration_minutes)
    step = dt.timedelta(minutes=step_minutes)

    out: list[Interval] = []
    d = start_date
    while d <= end_date:
        if d.weekday() not in weekdays:
            d += dt.timedelta(days=1)
            continue
        window_start = dt.datetime.combine(d, dt.time(work_start_hour, 0), tzinfo=JST)
        window_end = dt.datetime.combine(d, dt.time(work_end_hour, 0), tzinfo=JST)
        free = free_within_window(busy, window_start, window_end)
        for fs, fe in free:
            cur = fs
            while cur + duration <= fe:
                if cur >= now:
                    out.append((cur, cur + duration))
                cur += step
        d += dt.timedelta(days=1)
    return out


def create_event_with_meet(
    service,
    calendar_id: str,
    title: str,
    start: dt.datetime,
    end: dt.datetime,
    description: str = "",
    send_updates: str = "none",
) -> dict:
    """カレンダーにGoogle Meetリンク付き予定を作成して返す。
    calendar_id は対象カレンダーのID（メアドでもOK）。
    そのカレンダーへの書き込み権限が必要。"""
    event_body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Tokyo"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Tokyo"},
        "conferenceData": {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    return (
        service.events()
        .insert(
            calendarId=calendar_id,
            body=event_body,
            conferenceDataVersion=1,
            sendUpdates=send_updates,
        )
        .execute()
    )


def extract_meet_link(event: dict) -> str | None:
    cd = event.get("conferenceData", {})
    for entry in cd.get("entryPoints", []):
        if entry.get("entryPointType") == "video":
            return entry.get("uri")
    return event.get("hangoutLink")


def format_with_breakdown(
    results: list[tuple[dt.date, list[Interval], dict[str, list[Interval]]]],
    display_names: dict[str, str],
    email_order: list[str],
) -> str:
    """合算 + 人ごとの内訳（根拠確認用）。"""
    lines: list[str] = []
    for d, intervals, per_person in results:
        time_str = "空きなし" if not intervals else _fmt_intervals(intervals)
        lines.append(f"【{_date_label(d)}】{time_str}")
        for email in email_order:
            name = display_names.get(email, email)
            lines.append(f"  ├ {name}: {_fmt_intervals(per_person.get(email, []))}")
        lines.append("")
    return "\n".join(lines).rstrip()

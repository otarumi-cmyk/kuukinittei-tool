"""候補日程の提案: 担当者×期間×時間帯で、日ごとの連続空き時間帯を出して、DM用メッセージを生成。"""
import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st

import config
from calendar_client import fetch_busy, free_within_window
from template_store import load_templates, safe_format
from ui_helpers import check_password, get_calendar_service

JST = ZoneInfo("Asia/Tokyo")
_WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

st.set_page_config(
    page_title="候補日程の提案",
    page_icon="📨",
    initial_sidebar_state="expanded",
)
st.title("📨 候補日程の提案")
st.caption("担当者×期間×時間帯で、日ごとの連続空き時間帯を生成 → DMコピペ用テキストを出力。")

if not check_password():
    st.stop()


def fmt_time(t: dt.datetime) -> str:
    """11:00 -> '11時', 11:30 -> '11:30'"""
    if t.minute == 0:
        return f"{t.hour}時"
    return f"{t.hour}:{t.minute:02d}"


def fmt_range(s: dt.datetime, e: dt.datetime) -> str:
    """両端とも分が0なら '11~15時'、片方でも分があれば '11:30~15時' のように整形。"""
    s_whole = s.minute == 0
    e_whole = e.minute == 0
    if s_whole and e_whole:
        return f"{s.hour}~{e.hour}時"
    if s_whole and not e_whole:
        return f"{s.hour}時~{e.hour}:{e.minute:02d}"
    if not s_whole and e_whole:
        return f"{s.hour}:{s.minute:02d}~{e.hour}時"
    return f"{s.hour}:{s.minute:02d}~{e.hour}:{e.minute:02d}"


def fmt_date(d: dt.date) -> str:
    return f"{d.month}/{d.day}({_WEEKDAYS[d.weekday()]})"


# ===== 入力フォーム =====
email_to_name = config.DISPLAY_NAMES
name_to_email = {v: k for k, v in email_to_name.items()}

today = dt.datetime.now(JST).date()

_options = [email_to_name[e] for e in config.EMAILS]
_default_idx = _options.index("横山") if "横山" in _options else 0
staff_label = st.selectbox("担当者", options=_options, index=_default_idx)
staff_email = name_to_email[staff_label]
duration_min = config.BOOKING_DURATION.get(staff_email, 60)
hours = config.BOOKABLE_HOURS.get(
    staff_email, {"start": 10, "end": 22, "weekdays": list(range(7))}
)
st.caption(f"所要時間: {duration_min}分（{staff_label}）— これ未満の細切れ空きは除外")

col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input(
        "開始日", value=today + dt.timedelta(days=1), min_value=today
    )
with col_end:
    end_date = st.date_input(
        "終了日", value=today + dt.timedelta(days=14), min_value=today
    )

col_h1, col_h2 = st.columns(2)
with col_h1:
    work_start = st.number_input(
        "時間帯 開始（時）", min_value=0, max_value=23, value=hours["start"]
    )
with col_h2:
    work_end = st.number_input(
        "時間帯 終了（時）", min_value=1, max_value=24, value=hours["end"]
    )


if st.button("候補を生成", type="primary"):
    if start_date > end_date:
        st.error("開始日は終了日より前にしてください。")
    elif work_start >= work_end:
        st.error("時間帯の開始は終了より前にしてください。")
    else:
        try:
            with st.spinner("カレンダー取得中..."):
                service = get_calendar_service()
                tmin = dt.datetime.combine(start_date, dt.time(0, 0), tzinfo=JST)
                tmax = dt.datetime.combine(end_date, dt.time(23, 59), tzinfo=JST)
                busy_map = fetch_busy(service, [staff_email], tmin, tmax)
                busy = busy_map.get(staff_email, [])

            now = dt.datetime.now(JST)
            min_td = dt.timedelta(minutes=duration_min)
            weekdays = hours.get("weekdays", list(range(7)))

            lines: list[str] = []
            skipped: list[str] = []
            d = start_date
            while d <= end_date:
                if d.weekday() not in weekdays:
                    skipped.append(f"{fmt_date(d)}: 営業対象外の曜日")
                    d += dt.timedelta(days=1)
                    continue
                window_start = dt.datetime.combine(
                    d, dt.time(int(work_start), 0), tzinfo=JST
                )
                window_end = dt.datetime.combine(
                    d, dt.time(int(work_end), 0), tzinfo=JST
                )
                free = free_within_window(busy, window_start, window_end)
                # 過去の時間を除外
                free = [(max(s, now), e) for s, e in free if e > now]
                long_enough = [(s, e) for s, e in free if (e - s) >= min_td]
                short_only = [(s, e) for s, e in free if (e - s) < min_td]
                if long_enough:
                    ranges = ", ".join(fmt_range(s, e) for s, e in long_enough)
                    lines.append(f"・{fmt_date(d)} {ranges}")
                elif short_only:
                    short_ranges = ", ".join(fmt_range(s, e) for s, e in short_only)
                    skipped.append(
                        f"{fmt_date(d)}: 細切れの空きのみ ({short_ranges}) — {duration_min}分未満"
                    )
                else:
                    skipped.append(f"{fmt_date(d)}: 予定で埋まっています")
                d += dt.timedelta(days=1)

            if not lines:
                st.warning("候補が見つかりませんでした。期間や時間帯を広げてみてください。")
            else:
                st.success(f"{len(lines)}日分の候補を生成しました。")
                dm_text = safe_format(
                    load_templates()["suggest_dm"],
                    slots="\n".join(lines),
                    staff=staff_label,
                    duration=str(duration_min),
                )
                st.subheader("📋 DM貼り付け用")
                st.code(dm_text, language=None)

            if skipped:
                with st.expander(f"除外された日（{len(skipped)}件）", expanded=False):
                    for line in skipped:
                        st.write(f"- {line}")
        except Exception as ex:
            st.error(f"エラー: {ex}")
            st.exception(ex)

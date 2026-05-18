"""予約作成: インスタ名と開始日時だけ入力 → 自動で空いてるスタッフとフォンブースを選んで予約。"""
import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st

import config
from calendar_client import (
    create_event_with_meet,
    extract_meet_link,
    fetch_busy,
    find_free_resource,
)
from ui_helpers import check_password, get_calendar_service

JST = ZoneInfo("Asia/Tokyo")
_WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

st.set_page_config(
    page_title="予約作成",
    page_icon="📝",
    initial_sidebar_state="expanded",
)
st.title("📝 予約作成")
st.caption("インスタ名と開始日時を入れると、空いてる担当者と所要時間を自動で決めて予約します。")

if not check_password():
    st.stop()


def fmt_dt(d: dt.datetime) -> str:
    wd = _WEEKDAYS[d.weekday()]
    return f"{d.month}/{d.day}({wd}) {d.strftime('%H:%M')}"


def find_available_staff(service, start: dt.datetime) -> tuple[str | None, dt.datetime | None]:
    """config.EMAILS 順に試して、開始時刻から所要時間ぶん空いてる最初の担当者を返す。
    返り値: (staff_email, end_datetime) または (None, None)。"""
    for email in config.EMAILS:
        duration = config.BOOKING_DURATION.get(email, 60)
        end = start + dt.timedelta(minutes=duration)
        # 営業時間チェック
        hours = config.BOOKABLE_HOURS.get(email, {"start": 10, "end": 22, "weekdays": list(range(7))})
        if start.weekday() not in hours.get("weekdays", list(range(7))):
            continue
        if start.hour < hours["start"] or end.hour > hours["end"] or (end.hour == hours["end"] and end.minute > 0):
            continue
        busy_map = fetch_busy(service, [email], start, end)
        if not busy_map.get(email):  # 空のリスト = 空いてる
            return email, end
    return None, None


# ===== 入力フォーム =====
now = dt.datetime.now(JST)
tomorrow = now.date() + dt.timedelta(days=1)

insta_name = st.text_input("インスタ名", placeholder="例: tanaka_san")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("開始日", value=tomorrow, min_value=now.date())
with col2:
    start_time = st.time_input(
        "開始時間", value=dt.time(14, 0), step=dt.timedelta(minutes=30)
    )

if st.button("予約する", type="primary"):
    if not insta_name.strip():
        st.error("インスタ名を入力してください。")
    else:
        start_dt = dt.datetime.combine(start_date, start_time, tzinfo=JST)
        if start_dt < now:
            st.error("過去の日時は指定できません。")
        else:
            try:
                with st.spinner("空いてる担当者を検索中..."):
                    service = get_calendar_service()
                    staff_email, end_dt = find_available_staff(service, start_dt)

                if not staff_email:
                    st.error(
                        f"❌ その時間に空いてる担当者がいません（営業時間外、または全員予定あり）。\n\n"
                        f"指定時刻: {fmt_dt(start_dt)}\n\n"
                        f"別の時間で試してください。"
                    )
                else:
                    staff_label = config.DISPLAY_NAMES.get(staff_email, staff_email)
                    title = f"{insta_name.strip()}様 {config.DEFAULT_MEETING_TITLE}"

                    with st.spinner("空いてるフォンブースを検索中..."):
                        phone_box = find_free_resource(
                            service, config.PHONE_BOX_RESOURCES, start_dt, end_dt
                        )

                    attendees = [{"email": staff_email}]
                    if phone_box:
                        attendees.append({"email": phone_box, "resource": True})

                    description = (
                        f"インスタ名: {insta_name.strip()}\n"
                        f"担当: {staff_label}\n"
                        + (f"フォンブース: {config.PHONE_BOX_NAMES.get(phone_box, phone_box)}\n" if phone_box else "")
                        + "（kuukinittei ツールから自動作成）"
                    )

                    with st.spinner("予定を作成中..."):
                        event = create_event_with_meet(
                            service,
                            calendar_id="primary",
                            title=title,
                            start=start_dt,
                            end=end_dt,
                            description=description,
                            attendees=attendees,
                            send_updates="all",
                        )
                    meet_link = extract_meet_link(event)

                    st.success(f"🎉 予約完了！担当: **{staff_label}**（{(end_dt - start_dt).seconds // 60}分）")

                    if phone_box:
                        st.write(f"**フォンブース**: {config.PHONE_BOX_NAMES.get(phone_box)}")
                    else:
                        st.warning("⚠️ 空いてるフォンブースが見つかりませんでした。")
                    st.write(f"**日時**: {fmt_dt(start_dt)} 〜 {end_dt.strftime('%H:%M')}")
                    st.write(f"**タイトル**: {title}")
                    if event.get("htmlLink"):
                        st.markdown(f"[カレンダーで開く]({event['htmlLink']})")

                    dm_text = (
                        f"返信ありがとうございます！\n"
                        f"では、こちらのリンクからお願いいたします！\n\n"
                        f"日時: {fmt_dt(start_dt)} 〜 {end_dt.strftime('%H:%M')}\n"
                        f"リンク: {meet_link or '(Meetリンク取得失敗)'}"
                    )
                    st.subheader("📋 DM貼り付け用")
                    st.code(dm_text, language=None)

            except Exception as ex:
                st.error(f"エラー: {ex}")
                st.exception(ex)

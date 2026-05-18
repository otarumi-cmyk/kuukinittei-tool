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


# ===== 入力フォーム =====
now = dt.datetime.now(JST)
tomorrow = now.date() + dt.timedelta(days=1)

email_to_name = config.DISPLAY_NAMES
name_to_email = {v: k for k, v in email_to_name.items()}

col_staff, col_name = st.columns([1, 2])
with col_staff:
    staff_label = st.selectbox(
        "担当者", options=[email_to_name[e] for e in config.EMAILS]
    )
with col_name:
    insta_name = st.text_input("インスタ名", placeholder="例: tanaka_san")

staff_email = name_to_email[staff_label]
duration_min = config.BOOKING_DURATION.get(staff_email, 60)
st.caption(f"所要時間: {duration_min}分（{staff_label}）")

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
        end_dt = start_dt + dt.timedelta(minutes=duration_min)
        if start_dt < now:
            st.error("過去の日時は指定できません。")
        else:
            try:
                with st.spinner(f"{staff_label}さんの空き確認中..."):
                    service = get_calendar_service()
                    busy_map = fetch_busy(service, [staff_email], start_dt, end_dt)

                if busy_map.get(staff_email):
                    busy_str = ", ".join(
                        f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}"
                        for s, e in busy_map[staff_email]
                    )
                    st.error(
                        f"❌ {staff_label}さんはその時間に予定があります。\n\n"
                        f"指定: {fmt_dt(start_dt)} 〜 {end_dt.strftime('%H:%M')}\n"
                        f"既存予定: {busy_str}"
                    )
                else:
                    title = f"{insta_name.strip()}様 {config.DEFAULT_MEETING_TITLE}"

                    with st.spinner("空いてるフォンブースを検索中..."):
                        phone_box = find_free_resource(
                            service, config.PHONE_BOX_RESOURCES, start_dt, end_dt
                        )

                    attendees = [{"email": staff_email}]
                    if phone_box:
                        attendees.append({"email": phone_box, "resource": True})
                    # 通知先（任意参加者）
                    for notify in config.NOTIFY_EMAILS:
                        attendees.append({"email": notify, "optional": True})

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

                    st.success(f"🎉 予約完了！担当: **{staff_label}**（{duration_min}分）")

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

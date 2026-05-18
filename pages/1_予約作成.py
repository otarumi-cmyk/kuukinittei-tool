"""予約作成: 担当者の空き枠を表示し、選択した枠にMeet付き予定を作成。"""
import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st

import config
from calendar_client import (
    create_event_with_meet,
    extract_meet_link,
    fetch_busy,
    generate_candidate_slots,
)
from ui_helpers import check_password, get_calendar_service

JST = ZoneInfo("Asia/Tokyo")
_WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

st.set_page_config(page_title="予約作成", page_icon="📝")
st.title("📝 予約作成")
st.caption("担当者の空き枠から1つ選んで予約 → Meetリンク付きでカレンダー登録 → DMコピペ用テキスト生成。")

if not check_password():
    st.stop()


def fmt_date(d: dt.date) -> str:
    return f"{d.month}/{d.day}({_WEEKDAYS[d.weekday()]})"


def fmt_slot(s: dt.datetime, e: dt.datetime) -> str:
    return f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}"


# ===== 入力フォーム =====
today = dt.datetime.now(JST).date()
default_start = today + dt.timedelta(days=config.BOOKING_DEFAULT_START_OFFSET)
default_end = default_start + dt.timedelta(days=config.BOOKING_DEFAULT_RANGE_DAYS - 1)

email_to_name = config.DISPLAY_NAMES
name_to_email = {v: k for k, v in email_to_name.items()}

col1, col2 = st.columns([1, 2])
with col1:
    staff_label = st.selectbox(
        "担当者", options=[email_to_name[e] for e in config.EMAILS]
    )
with col2:
    insta_name = st.text_input("インスタ名（タイトル前置き）", placeholder="例: tanaka_san")

col3, col4 = st.columns([1, 1])
with col3:
    title_suffix = st.text_input(
        "面談タイトル", value=config.DEFAULT_MEETING_TITLE
    )
with col4:
    staff_email = name_to_email[staff_label]
    default_duration = config.BOOKING_DURATION.get(staff_email, 60)
    duration = st.number_input(
        "所要時間（分）", min_value=15, max_value=240, value=default_duration, step=15
    )

col5, col6 = st.columns(2)
with col5:
    start_date = st.date_input("開始日", value=default_start, min_value=today)
with col6:
    end_date = st.date_input("終了日", value=default_end, min_value=today)

hours = config.BOOKABLE_HOURS.get(staff_email, {"start": 10, "end": 22})
col7, col8 = st.columns(2)
with col7:
    work_start = st.number_input(
        "時間帯 開始（時）", min_value=0, max_value=23, value=hours["start"]
    )
with col8:
    work_end = st.number_input(
        "時間帯 終了（時）", min_value=1, max_value=24, value=hours["end"]
    )

# ===== 空き枠取得 =====
if st.button("空き枠を取得", type="primary"):
    if start_date > end_date:
        st.error("開始日は終了日より前の日付にしてください。")
    elif work_start >= work_end:
        st.error("時間帯の開始は終了より前にしてください。")
    elif not insta_name.strip():
        st.error("インスタ名を入力してください。")
    else:
        try:
            with st.spinner("カレンダー取得中..."):
                service = get_calendar_service()
                tmin = dt.datetime.combine(start_date, dt.time(0, 0), tzinfo=JST)
                tmax = dt.datetime.combine(end_date, dt.time(23, 59), tzinfo=JST)
                busy_map = fetch_busy(service, [staff_email], tmin, tmax)
                slots = generate_candidate_slots(
                    busy=busy_map.get(staff_email, []),
                    start_date=start_date,
                    end_date=end_date,
                    work_start_hour=int(work_start),
                    work_end_hour=int(work_end),
                    duration_minutes=int(duration),
                    step_minutes=30,
                    weekdays=hours.get("weekdays"),
                )
            st.session_state.candidate_slots = slots
            st.session_state.staff_email = staff_email
            st.session_state.staff_label = staff_label
            st.session_state.insta_name = insta_name.strip()
            st.session_state.title_suffix = title_suffix.strip() or config.DEFAULT_MEETING_TITLE
            st.session_state.duration = int(duration)
            if not slots:
                st.warning("該当の空き枠が見つかりませんでした。期間や時間帯を広げてみてください。")
        except Exception as e:
            st.error(f"エラー: {e}")
            st.exception(e)

# ===== 空き枠表示と予約確定 =====
slots = st.session_state.get("candidate_slots", [])
if slots:
    st.divider()
    st.subheader(f"📋 {st.session_state.staff_label} の空き枠（{len(slots)}件）")
    st.caption(f"クリックすると 「{st.session_state.insta_name}様 {st.session_state.title_suffix}」 として確定します。")

    # 日別にグルーピングして表示
    by_day: dict[dt.date, list] = {}
    for s, e in slots:
        by_day.setdefault(s.date(), []).append((s, e))

    for d, day_slots in by_day.items():
        st.markdown(f"**{fmt_date(d)}**")
        cols = st.columns(4)
        for i, (s, e) in enumerate(day_slots):
            with cols[i % 4]:
                if st.button(fmt_slot(s, e), key=f"slot-{s.isoformat()}"):
                    st.session_state.selected_slot = (s, e)

# ===== 予約確定処理 =====
if st.session_state.get("selected_slot") and not st.session_state.get("booking_result"):
    s, e = st.session_state.selected_slot
    st.divider()
    title = f"{st.session_state.insta_name}様 {st.session_state.title_suffix}"
    st.info(
        f"**確認**\n\n"
        f"- 担当: {st.session_state.staff_label}\n"
        f"- タイトル: {title}\n"
        f"- 日時: {fmt_date(s.date())} {fmt_slot(s, e)}"
    )
    confirm_col, cancel_col = st.columns([1, 1])
    with confirm_col:
        if st.button("✅ 予約確定", type="primary"):
            try:
                with st.spinner("予定を作成中..."):
                    service = get_calendar_service()
                    description = (
                        f"インスタ名: {st.session_state.insta_name}\n"
                        f"担当: {st.session_state.staff_label}\n"
                        f"（kuukinittei ツールから自動作成）"
                    )
                    event = create_event_with_meet(
                        service,
                        calendar_id=st.session_state.staff_email,
                        title=title,
                        start=s,
                        end=e,
                        description=description,
                    )
                st.session_state.booking_result = event
            except Exception as ex:
                msg = str(ex)
                if "403" in msg or "permission" in msg.lower() or "forbidden" in msg.lower():
                    st.error(
                        f"予定作成に失敗しました（権限不足）。\n\n"
                        f"対策: {st.session_state.staff_label} さんのGoogleカレンダーで、"
                        f"o.tarumi@migi-nanameue.co.jp に「予定の変更権限」を共有してください。\n\n"
                        f"詳細エラー: {msg}"
                    )
                else:
                    st.error(f"エラー: {msg}")
    with cancel_col:
        if st.button("✖️ キャンセル"):
            st.session_state.selected_slot = None
            st.rerun()

# ===== 結果表示 =====
if st.session_state.get("booking_result"):
    event = st.session_state.booking_result
    s, e = st.session_state.selected_slot
    meet_link = extract_meet_link(event)

    st.divider()
    st.success("🎉 予約完了！")

    if meet_link:
        st.write(f"**Meetリンク**: {meet_link}")
    st.write(f"**日時**: {fmt_date(s.date())} {fmt_slot(s, e)}")
    st.write(f"**タイトル**: {event.get('summary')}")
    if event.get("htmlLink"):
        st.write(f"[カレンダーで開く]({event['htmlLink']})")

    # DM用テキスト
    dm_text = (
        f"返信ありがとうございます！\n"
        f"では、こちらのリンクからお願いいたします！\n\n"
        f"日時: {fmt_date(s.date())} {fmt_slot(s, e)}\n"
        f"リンク: {meet_link or '(Meetリンク取得失敗)'}"
    )
    st.subheader("📋 DM貼り付け用")
    st.code(dm_text, language=None)

    if st.button("🔄 新しい予約を作る"):
        for k in ("candidate_slots", "selected_slot", "booking_result"):
            st.session_state.pop(k, None)
        st.rerun()

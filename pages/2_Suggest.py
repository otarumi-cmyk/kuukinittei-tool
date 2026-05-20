"""候補日程の提案: 担当者×期間で空き枠を候補として出して、DM用メッセージを生成。"""
import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st

import config
from calendar_client import fetch_busy, generate_candidate_slots
from ui_helpers import check_password, get_calendar_service

JST = ZoneInfo("Asia/Tokyo")
_WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

st.set_page_config(
    page_title="候補日程の提案",
    page_icon="📨",
    initial_sidebar_state="expanded",
)
st.title("📨 候補日程の提案")
st.caption("担当者と期間を指定して、空いてる候補日程を生成 → DMコピペ用テキストを出力。")

if not check_password():
    st.stop()


def fmt_slot(s: dt.datetime, e: dt.datetime) -> str:
    wd = _WEEKDAYS[s.weekday()]
    return f"{s.month}/{s.day}({wd}) {s.strftime('%H:%M')}-{e.strftime('%H:%M')}"


# ===== 入力フォーム =====
email_to_name = config.DISPLAY_NAMES
name_to_email = {v: k for k, v in email_to_name.items()}

today = dt.datetime.now(JST).date()

col_staff, col_n, col_per = st.columns([1, 1, 1])
with col_staff:
    staff_label = st.selectbox(
        "担当者", options=[email_to_name[e] for e in config.EMAILS]
    )
with col_n:
    n_proposals = st.number_input("候補数（最大）", min_value=1, max_value=20, value=5)
with col_per:
    per_day = st.number_input("1日あたりの最大枠", min_value=1, max_value=5, value=1)

staff_email = name_to_email[staff_label]
duration_min = config.BOOKING_DURATION.get(staff_email, 60)
hours = config.BOOKABLE_HOURS.get(
    staff_email, {"start": 10, "end": 22, "weekdays": list(range(7))}
)
st.caption(f"所要時間: {duration_min}分（{staff_label}）")

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
                all_slots = generate_candidate_slots(
                    busy=busy_map.get(staff_email, []),
                    start_date=start_date,
                    end_date=end_date,
                    work_start_hour=int(work_start),
                    work_end_hour=int(work_end),
                    duration_minutes=duration_min,
                    step_minutes=30,
                    weekdays=hours.get("weekdays"),
                )

            # 1日あたり最大 per_day 枠まで、合計 n_proposals 件まで選ぶ
            per_date_count: dict[dt.date, int] = {}
            selected: list[tuple[dt.datetime, dt.datetime]] = []
            for s, e in all_slots:
                if len(selected) >= int(n_proposals):
                    break
                d = s.date()
                if per_date_count.get(d, 0) >= int(per_day):
                    continue
                selected.append((s, e))
                per_date_count[d] = per_date_count.get(d, 0) + 1

            if not selected:
                st.warning("候補が見つかりませんでした。期間や時間帯を広げてみてください。")
            else:
                st.success(f"候補 {len(selected)}件を生成しました。")
                bullets = "\n".join(f"・{fmt_slot(s, e)}" for s, e in selected)
                dm_text = (
                    f"以下の日程が空いております！\n"
                    f"こちらの日程のご都合はいかがでしょうか✨\n\n"
                    f"{bullets}"
                )
                st.subheader("📋 DM貼り付け用")
                st.code(dm_text, language=None)
        except Exception as ex:
            st.error(f"エラー: {ex}")
            st.exception(ex)

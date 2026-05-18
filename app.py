"""Streamlit UI: 空き日程ジェネレーター（DM向けの合算空き枠を出力）。"""
import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st

import config
from calendar_client import (
    compute_daily_union,
    format_union_only,
    format_with_breakdown,
)
from ui_helpers import check_password, get_calendar_service

JST = ZoneInfo("Asia/Tokyo")

st.set_page_config(page_title="空き日程ジェネレーター", page_icon="📅")
st.title("📅 空き日程ジェネレーター")
st.caption("指定期間の中で、3人のうち誰かが空いてる時間帯をまとめて出します。")

if not check_password():
    st.stop()

today = dt.datetime.now(JST).date()
default_start = today + dt.timedelta(days=config.DEFAULT_START_OFFSET)
default_end = default_start + dt.timedelta(days=config.DEFAULT_RANGE_DAYS - 1)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("開始日", value=default_start, min_value=today)
with col2:
    end_date = st.date_input("終了日", value=default_end, min_value=today)

with st.expander("現在の設定", expanded=False):
    for email in config.EMAILS:
        name = config.DISPLAY_NAMES.get(email, email)
        mins = config.MIN_SLOT_MINUTES.get(email, 0)
        st.write(f"- {name}（{email}）: 最低 {mins}分以上の空き")
    st.write(f"営業時間: {config.WORK_START_HOUR}:00 - {config.WORK_END_HOUR}:00")

if st.button("生成", type="primary"):
    if start_date > end_date:
        st.error("開始日は終了日より前の日付にしてください。")
    else:
        try:
            with st.spinner("カレンダー取得中..."):
                service = get_calendar_service()
                results = compute_daily_union(
                    service,
                    config.EMAILS,
                    start_date=start_date,
                    end_date=end_date,
                    work_start_hour=config.WORK_START_HOUR,
                    work_end_hour=config.WORK_END_HOUR,
                    min_slot_minutes=config.MIN_SLOT_MINUTES,
                )
                union_text = format_union_only(results)
                breakdown_text = format_with_breakdown(
                    results, config.DISPLAY_NAMES, config.EMAILS
                )

            st.success(f"生成完了！（{start_date} 〜 {end_date}, {len(results)}日間）")

            st.subheader("📋 DM貼り付け用（合算のみ）")
            st.code(union_text, language=None)

            st.subheader("🔍 内訳（根拠確認用）")
            st.code(breakdown_text, language=None)
        except FileNotFoundError as e:
            st.error(f"認証ファイルが見つかりません: {e}")
        except Exception as e:
            st.error(f"エラー: {e}")
            st.exception(e)

"""DM文言テンプレートの編集 + 保存。"""
import streamlit as st

import config
from template_store import load_templates, reset_templates, save_templates
from ui_helpers import check_password

st.set_page_config(
    page_title="テンプレート編集",
    page_icon="✏️",
    initial_sidebar_state="expanded",
)
st.title("✏️ テンプレート編集")
st.caption("Booking / Suggest のDM文言を自分用にカスタマイズ。保存すると次回以降も適用されます。")

if not check_password():
    st.stop()

# 現在のテンプレを読込
current = load_templates()

st.subheader("📝 Booking（予約完了後のDM）")
st.caption(
    "使えるプレースホルダー: `{datetime}` / `{link}` / `{staff}` / `{insta}` / `{title}` / `{phone_box}`"
)
booking_text = st.text_area(
    "Booking テンプレート",
    value=current["booking_dm"],
    height=180,
    key="booking_tpl",
    label_visibility="collapsed",
)

st.subheader("📨 Suggest（候補日程DM）")
st.caption(
    "使えるプレースホルダー: `{slots}` / `{staff}` / `{duration}`"
)
suggest_text = st.text_area(
    "Suggest テンプレート",
    value=current["suggest_dm"],
    height=180,
    key="suggest_tpl",
    label_visibility="collapsed",
)

col_save, col_reset = st.columns([1, 1])
with col_save:
    if st.button("💾 保存", type="primary"):
        save_templates({"booking_dm": booking_text, "suggest_dm": suggest_text})
        st.success("保存しました。Booking / Suggest ページで反映されます。")
with col_reset:
    if st.button("↺ デフォルトに戻す"):
        reset_templates()
        st.success("デフォルトに戻しました。ページを再読込してください。")

st.divider()
with st.expander("プレースホルダーの使用例", expanded=False):
    st.markdown("""
**Booking 例（プレースホルダ全部入り）**:
```
{insta}様のご予約を承りました。

担当: {staff}
日時: {datetime}
{phone_box}でお待ちしております。

Meetリンク: {link}
```

**Suggest 例**:
```
{staff}の{duration}分枠でご案内です✨

以下からお選びください！

{slots}
```
    """)

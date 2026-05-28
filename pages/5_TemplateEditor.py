"""開発用: 全テンプレート一覧 & インライン編集"""
import datetime
import streamlit as st

from line_template_store import (
    CATEGORIES,
    load_line_templates,
    save_line_templates,
    reset_line_templates,
    get_templates_mtime,
)
from ui_helpers import check_password

st.set_page_config(
    page_title="テンプレ編集（Dev）",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.title("🛠️ テンプレート一括編集")
st.caption("全テンプレートを一覧表示。文言の修正・タグ編集・削除がその場でできます。保存すると全員に自動反映されます。")

if not check_password():
    st.stop()

# ---------- 自動同期: ファイルが更新されたらセッションを自動リロード ----------
current_mtime = get_templates_mtime()
if "dev_mtime" not in st.session_state:
    st.session_state.dev_mtime = current_mtime

if current_mtime > st.session_state.dev_mtime:
    st.session_state.dev_templates = load_line_templates()
    st.session_state.dev_mtime = current_mtime
    st.toast("🔄 他のメンバーがテンプレートを更新しました！最新版を読み込みました")

# ---------- 読み込み ----------
if "dev_templates" not in st.session_state:
    st.session_state.dev_templates = load_line_templates()
    st.session_state.dev_mtime = current_mtime

templates = st.session_state.dev_templates
cat_labels = {c["id"]: c["label"] for c in CATEGORIES}
cat_ids = {c["label"]: c["id"] for c in CATEGORIES}

# ---------- フィルタ ----------
col_filter1, col_filter2 = st.columns([1, 2])
with col_filter1:
    filter_cat = st.selectbox(
        "カテゴリ絞り込み",
        ["全て"] + [c["label"] for c in CATEGORIES],
        key="dev_filter_cat",
    )
with col_filter2:
    filter_text = st.text_input(
        "テキスト検索（シチュエーション・本文）",
        placeholder="キモい文言をここで検索...",
        key="dev_filter_text",
    )

pool = list(templates)
if filter_cat != "全て":
    fid = cat_ids.get(filter_cat)
    pool = [t for t in pool if t.get("category") == fid]
if filter_text.strip():
    q = filter_text.strip().lower()
    pool = [
        t for t in pool
        if q in t.get("situation", "").lower()
        or q in t.get("body", "").lower()
        or q in " ".join(t.get("tags", [])).lower()
    ]

st.markdown(f"### 表示中: **{len(pool)}** / {len(templates)} 件")

# ---------- 変更トラッカー ----------
if "dev_changed" not in st.session_state:
    st.session_state.dev_changed = set()

# ---------- 一覧 ----------
for idx, t in enumerate(pool):
    tid = t["id"]
    cat_name = cat_labels.get(t.get("category", ""), "?")
    is_changed = tid in st.session_state.dev_changed

    header_color = "🟡" if is_changed else ""
    with st.container(border=True):
        # ヘッダー行
        h_col1, h_col2, h_col3 = st.columns([3, 1, 1])
        with h_col1:
            st.markdown(
                f"{'🟡 ' if is_changed else ''}"
                f"**{t['situation']}**　`{tid}`"
            )
        with h_col2:
            st.caption(cat_name)
        with h_col3:
            if st.button("🗑 削除", key=f"devdel_{tid}_{idx}"):
                st.session_state.dev_templates = [
                    x for x in st.session_state.dev_templates if x["id"] != tid
                ]
                save_line_templates(st.session_state.dev_templates)
                st.session_state.dev_mtime = get_templates_mtime()
                st.toast(f"「{t['situation']}」を削除しました（全員に反映されます）")
                st.rerun()

        # 編集フォーム
        col_left, col_right = st.columns([3, 2])

        with col_left:
            new_body = st.text_area(
                "本文",
                value=t["body"],
                height=180,
                key=f"devbody_{tid}_{idx}",
                label_visibility="collapsed",
            )

        with col_right:
            new_sit = st.text_input(
                "シチュエーション",
                value=t["situation"],
                key=f"devsit_{tid}_{idx}",
            )
            new_tags_str = st.text_input(
                "タグ（カンマ区切り）",
                value=", ".join(t.get("tags", [])),
                key=f"devtags_{tid}_{idx}",
            )
            new_cat_label = st.selectbox(
                "カテゴリ",
                [c["label"] for c in CATEGORIES],
                index=next(
                    (i for i, c in enumerate(CATEGORIES) if c["id"] == t.get("category")),
                    0,
                ),
                key=f"devcat_{tid}_{idx}",
            )

            # 保存ボタン
            if st.button("💾 保存", key=f"devsave_{tid}_{idx}", type="primary"):
                new_tags = [
                    s.strip()
                    for s in new_tags_str.replace("、", ",").split(",")
                    if s.strip()
                ]
                # テンプレート本体を更新
                for tmpl in st.session_state.dev_templates:
                    if tmpl["id"] == tid:
                        tmpl["situation"] = new_sit.strip() or t["situation"]
                        tmpl["body"] = new_body
                        tmpl["tags"] = new_tags
                        tmpl["category"] = cat_ids.get(new_cat_label, t.get("category"))
                        break
                save_line_templates(st.session_state.dev_templates)
                st.session_state.dev_mtime = get_templates_mtime()
                st.session_state.dev_changed.add(tid)
                st.toast(f"「{new_sit}」を保存しました ✅（全員に反映されます）")
                st.rerun()

# ---------- フッター ----------
st.divider()

# 最終更新タイムスタンプ表示
mtime = get_templates_mtime()
if mtime > 0:
    dt = datetime.datetime.fromtimestamp(mtime)
    st.caption(f"📄 最終更新: {dt:%m/%d %H:%M} · 保存するとチーム全員に自動反映されます")

col_b1, col_b2, col_b3 = st.columns(3)
with col_b1:
    changed_count = len(st.session_state.dev_changed)
    if changed_count:
        st.success(f"🟡 このセッションで {changed_count} 件を編集済み（全員に反映済み）")
with col_b2:
    if st.button("🔄 最新に更新", key="dev_reload"):
        st.session_state.dev_templates = load_line_templates()
        st.session_state.dev_mtime = get_templates_mtime()
        st.session_state.dev_changed = set()
        st.toast("最新版を読み込みました ✅")
        st.rerun()
with col_b3:
    if st.button("↺ デフォルトに全リセット", key="dev_reset"):
        reset_line_templates()
        st.session_state.dev_templates = load_line_templates()
        st.session_state.dev_mtime = get_templates_mtime()
        st.session_state.dev_changed = set()
        st.toast("デフォルトに戻しました（全員に反映されます）")
        st.rerun()

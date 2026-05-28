"""LINE返信補助: シチュエーション別テンプレートの検索・編集・コピー"""
import streamlit as st

from line_template_store import (
    CATEGORIES,
    QUALITY_CHECKLIST,
    load_line_templates,
    save_line_templates,
    reset_line_templates,
    search_templates,
)
from ui_helpers import check_password

st.set_page_config(
    page_title="LINE返信補助",
    page_icon="💬",
    initial_sidebar_state="expanded",
)
st.title("💬 LINE返信補助")
st.caption(
    "相手の返信内容に合わせて、おすすめのテンプレートを表示。"
    "その場で編集してコピーできます。"
)

if not check_password():
    st.stop()

# テンプレ読み込み
if "line_templates" not in st.session_state:
    st.session_state.line_templates = load_line_templates()

templates = st.session_state.line_templates
cat_labels = {c["id"]: c["label"] for c in CATEGORIES}


def _split_body(body: str) -> tuple[str, str]:
    """本文を共感パート(1通目)とクロージングパート(2通目)に分割。
    最後の空行(\n\n)で分ける。空行がなければ全体を1通目とする。"""
    pos = body.rfind("\n\n")
    if pos == -1:
        return body, ""
    return body[:pos].strip(), body[pos:].strip()


# ===== 検索 =====
query = st.text_input(
    "相手の返信内容・キーワード",
    placeholder="例: 上司がきつい、残業多い、キャンセル...",
)

# カテゴリ選択
cat_options = ["全て"] + [c["label"] for c in CATEGORIES]
selected_cat_label = st.radio(
    "カテゴリ",
    cat_options,
    horizontal=True,
    label_visibility="collapsed",
)
selected_cat_id = None
for c in CATEGORIES:
    if c["label"] == selected_cat_label:
        selected_cat_id = c["id"]
        break

# フィルタ
pool = templates
if selected_cat_id:
    pool = [t for t in pool if t.get("category") == selected_cat_id]
if query.strip():
    pool = search_templates(pool, query)

# シチュエーション選択
situations = [t["situation"] for t in pool]
if situations:
    selected_sit = st.pills(
        "シチュエーション",
        situations,
        label_visibility="collapsed",
    )
    if selected_sit:
        pool = [t for t in pool if t["situation"] == selected_sit]

# ===== 結果表示 =====
st.caption(f"{len(pool)}件のテンプレート")

for i, t in enumerate(pool):
    cat_name = cat_labels.get(t.get("category", ""), "")
    tags_str = " ".join(f"#{tag}" for tag in t.get("tags", []))
    part1, part2 = _split_body(t["body"])

    with st.container(border=True):
        col_title, col_tags = st.columns([1, 2])
        with col_title:
            st.markdown(f"**{t['situation']}**")
        with col_tags:
            st.caption(f"{cat_name} · {tags_str}")

        # --- 1通目: 共感パート ---
        st.caption("① 共感（1通目）")
        edited1 = st.text_area(
            "1通目",
            value=part1,
            height=140,
            key=f"line_p1_{t['id']}_{i}",
            label_visibility="collapsed",
        )
        st.code(edited1, language=None)

        # --- 2通目: クロージングパート ---
        if part2:
            st.caption("② クロージング（2通目）")
            edited2 = st.text_area(
                "2通目",
                value=part2,
                height=80,
                key=f"line_p2_{t['id']}_{i}",
                label_visibility="collapsed",
            )
            st.code(edited2, language=None)

# ===== 品質チェックリスト =====
with st.expander("✅ 品質チェックリスト"):
    for item in QUALITY_CHECKLIST:
        st.checkbox(item, key=f"qc_{item}")

# ===== テンプレ管理 =====
with st.expander("🔧 テンプレート管理"):
    st.subheader("➕ 新規追加")
    new_cat = st.selectbox(
        "カテゴリ",
        [c["label"] for c in CATEGORIES],
        key="line_new_cat",
    )
    new_cat_id = next(
        (c["id"] for c in CATEGORIES if c["label"] == new_cat), "relationship"
    )
    new_sit = st.text_input("シチュエーション名", key="line_new_sit")
    new_tags = st.text_input("タグ（カンマ区切り）", key="line_new_tags")
    new_body = st.text_area("返信テンプレート（1通目）", height=120, key="line_new_body")
    new_body2 = st.text_area(
        "クロージング（2通目・空欄なら1通で完結）",
        height=80,
        key="line_new_body2",
    )

    if st.button("追加する", type="primary", key="line_add"):
        if new_sit.strip() and new_body.strip():
            tags = [
                s.strip()
                for s in new_tags.replace("、", ",").split(",")
                if s.strip()
            ]
            full_body = new_body.strip()
            if new_body2.strip():
                full_body += "\n\n" + new_body2.strip()
            st.session_state.line_templates.append(
                {
                    "id": f"custom_{len(templates)}",
                    "category": new_cat_id,
                    "situation": new_sit.strip(),
                    "tags": tags,
                    "body": full_body,
                }
            )
            save_line_templates(st.session_state.line_templates)
            st.success(f"「{new_sit}」を追加しました")
            st.rerun()
        else:
            st.error("シチュエーション名と本文は必須です")

    st.divider()
    st.subheader(f"📝 登録済み（{len(templates)}件）")
    for t in templates:
        col_info, col_del = st.columns([4, 1])
        with col_info:
            cn = cat_labels.get(t.get("category", ""), "")
            st.markdown(
                f"**{t['situation']}** · {cn} · "
                + " ".join(f"`#{tag}`" for tag in t.get("tags", []))
            )
        with col_del:
            if st.button("削除", key=f"del_{t['id']}"):
                st.session_state.line_templates = [
                    x for x in st.session_state.line_templates if x["id"] != t["id"]
                ]
                save_line_templates(st.session_state.line_templates)
                st.rerun()

    st.divider()
    if st.button("↺ デフォルトに戻す", key="line_reset"):
        reset_line_templates()
        st.session_state.line_templates = load_line_templates()
        st.success("デフォルトに戻しました")
        st.rerun()

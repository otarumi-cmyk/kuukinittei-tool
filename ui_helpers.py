"""Streamlit共通ヘルパー（認証ゲートと Calendar service の取得）。"""
import json

import streamlit as st

import config
from calendar_client import get_service, get_service_from_token_info


def _get_secret(key: str, default=None):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


def check_password() -> bool:
    """secrets に app_password がある場合のみ認証を要求。"""
    correct = _get_secret("app_password")
    if not correct:
        return True
    if st.session_state.get("authed"):
        return True

    pw = st.text_input("🔒 パスワードを入力", type="password")
    if pw:
        if pw == correct:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    return False


def get_calendar_service():
    """secrets にトークンがあればそれを使い、無ければローカルファイルから読む。"""
    token_info_str = _get_secret("token_json")
    if token_info_str:
        return get_service_from_token_info(json.loads(token_info_str))
    return get_service(config.CLIENT_SECRETS_FILE, config.TOKEN_FILE)

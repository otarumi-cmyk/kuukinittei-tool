"""DM文言テンプレートの保存・読込（templates.json）。
Streamlit Cloud のファイルシステムに保存。再デプロイで消えるので、その際は
config.py の DEFAULT_TEMPLATES が使われる。"""
import json
from pathlib import Path

import config

TEMPLATES_FILE = Path("templates.json")


def load_templates() -> dict[str, str]:
    """保存済みテンプレートを読込。なければデフォルトを返す。"""
    result = dict(config.DEFAULT_TEMPLATES)
    if TEMPLATES_FILE.exists():
        try:
            saved = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
            for k in result.keys():
                if k in saved and isinstance(saved[k], str):
                    result[k] = saved[k]
        except Exception:
            pass
    return result


def save_templates(templates: dict[str, str]) -> None:
    TEMPLATES_FILE.write_text(
        json.dumps(templates, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def reset_templates() -> None:
    if TEMPLATES_FILE.exists():
        TEMPLATES_FILE.unlink()


def safe_format(template: str, **kwargs) -> str:
    """{key} を kwargs で埋める。kwargsにないキーはそのまま残す。"""
    class _Default(dict):
        def __missing__(self, key):
            return "{" + key + "}"
    return template.format_map(_Default(**kwargs))

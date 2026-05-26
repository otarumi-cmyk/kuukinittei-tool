"""DM文言テンプレートの保存・読込（templates.json）。
config に DEFAULT_TEMPLATES が無くても落ちないよう、フォールバックを内蔵。"""
import json
from pathlib import Path

TEMPLATES_FILE = Path("templates.json")

# config.DEFAULT_TEMPLATES が無い/読めない場合のフォールバック
_FALLBACK_TEMPLATES = {
    "booking_dm": (
        "返信ありがとうございます！\n"
        "では、こちらのリンクからお願いいたします！\n\n"
        "日時: {datetime}\n"
        "リンク: {link}"
    ),
    "suggest_dm": (
        "以下の日程が空いております！\n"
        "こちらの日程のご都合はいかがでしょうか✨\n\n"
        "{slots}"
    ),
}


def _get_defaults() -> dict[str, str]:
    """config.DEFAULT_TEMPLATES があればそれを、無ければ内蔵フォールバックを返す。"""
    result = dict(_FALLBACK_TEMPLATES)
    try:
        import config
        cfg_defaults = getattr(config, "DEFAULT_TEMPLATES", None)
        if isinstance(cfg_defaults, dict):
            for k, v in cfg_defaults.items():
                if isinstance(v, str):
                    result[k] = v
    except Exception:
        pass
    return result


def load_templates() -> dict[str, str]:
    """デフォルト + 保存済みテンプレ をマージして返す。常に動く。"""
    result = _get_defaults()
    if TEMPLATES_FILE.exists():
        try:
            saved = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
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

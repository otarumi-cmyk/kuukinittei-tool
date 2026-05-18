"""ツールの設定。必要に応じて書き換えてください。"""

# OAuthクライアントシークレットJSON（GCPでダウンロードしたファイル）
CLIENT_SECRETS_FILE = "client_secret.json"

# OAuth認証後にアクセストークンをキャッシュするファイル（自動生成）
TOKEN_FILE = "token.json"

# 対象3人のGoogleカレンダーアドレス（同じWorkspaceドメイン内の3人）
EMAILS = [
    "y.hiraga@migi-nanameue.co.jp",
    "kotaro.suzuki@migi-nanameue.co.jp",
    "d.yokoyama@migi-nanameue.co.jp",
]

# 表示名（インスタDM用に短く）
DISPLAY_NAMES = {
    "y.hiraga@migi-nanameue.co.jp": "平賀",
    "kotaro.suzuki@migi-nanameue.co.jp": "鈴木",
    "d.yokoyama@migi-nanameue.co.jp": "横山",
}

# 人ごとの最低空き枠（分）— これ未満の細切れ空きは無視
MIN_SLOT_MINUTES = {
    "y.hiraga@migi-nanameue.co.jp": 90,        # 1.5h
    "kotaro.suzuki@migi-nanameue.co.jp": 90,   # 1.5h
    "d.yokoyama@migi-nanameue.co.jp": 60,      # 1h
}

# 営業時間（JST）
WORK_START_HOUR = 10
WORK_END_HOUR = 22

# UIの初期表示: 何日後から（2=翌々日）何日間を見るか
DEFAULT_START_OFFSET = 2  # 翌々日
DEFAULT_RANGE_DAYS = 3    # 3日間

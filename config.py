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

# ===== 予約作成ページの設定 =====

# 担当者ごとの面談時間（分）
BOOKING_DURATION = {
    "y.hiraga@migi-nanameue.co.jp": 90,
    "kotaro.suzuki@migi-nanameue.co.jp": 90,
    "d.yokoyama@migi-nanameue.co.jp": 60,
}

# 担当者ごとの予約可能時間帯（JST, 24h）と曜日（0=月, 6=日）
BOOKABLE_HOURS = {
    "y.hiraga@migi-nanameue.co.jp": {
        "start": 10, "end": 22, "weekdays": [0, 1, 2, 3, 4, 5, 6],
    },
    "kotaro.suzuki@migi-nanameue.co.jp": {
        "start": 10, "end": 22, "weekdays": [0, 1, 2, 3, 4, 5, 6],
    },
    "d.yokoyama@migi-nanameue.co.jp": {
        "start": 10, "end": 22, "weekdays": [0, 1, 2, 3, 4, 5, 6],
    },
}

# 予約画面のデフォルト期間
BOOKING_DEFAULT_START_OFFSET = 2   # 翌々日から
BOOKING_DEFAULT_RANGE_DAYS = 14    # 2週間先まで

# デフォルトの面談タイトル（インスタ名の後ろにつく）
DEFAULT_MEETING_TITLE = "初回面談"

# 予約時に自動アサインされるフォンブース（空いてる順に選ぶ）
PHONE_BOX_RESOURCES = [
    "c_1881pr03kdt28g58ncn5mq2g2mch6@resource.calendar.google.com",  # 5F-A
    "c_188e8la9c1huejb8l65e8env61j08@resource.calendar.google.com",  # 5F-B
    "c_188468t6mf1raib0h2dvksel4k0pe@resource.calendar.google.com",  # 5F-C
    "c_1889bk6nq2veshmkieduuv9ta76n8@resource.calendar.google.com",  # 5F-D
    "c_1889u9g33evpkjafldgjlhc80pp0u@resource.calendar.google.com",  # 5F-E
    "c_188d4pcs4v7tqhephrchcbmt155uk@resource.calendar.google.com",  # 5F-F
    "c_1881fa69dbjn4je0g6hm9s5k4n5uk@resource.calendar.google.com",  # 3F-G
    "c_1881fbkj3nt8oh3dg67oi0l1hplmq@resource.calendar.google.com",  # 3F-H
    "c_1884tlds0t7eehujnnu0limapch04@resource.calendar.google.com",  # 3F-I
]
PHONE_BOX_NAMES = {
    "c_1881pr03kdt28g58ncn5mq2g2mch6@resource.calendar.google.com": "5F-A",
    "c_188e8la9c1huejb8l65e8env61j08@resource.calendar.google.com": "5F-B",
    "c_188468t6mf1raib0h2dvksel4k0pe@resource.calendar.google.com": "5F-C",
    "c_1889bk6nq2veshmkieduuv9ta76n8@resource.calendar.google.com": "5F-D",
    "c_1889u9g33evpkjafldgjlhc80pp0u@resource.calendar.google.com": "5F-E",
    "c_188d4pcs4v7tqhephrchcbmt155uk@resource.calendar.google.com": "5F-F",
    "c_1881fa69dbjn4je0g6hm9s5k4n5uk@resource.calendar.google.com": "3F-G",
    "c_1881fbkj3nt8oh3dg67oi0l1hplmq@resource.calendar.google.com": "3F-H",
    "c_1884tlds0t7eehujnnu0limapch04@resource.calendar.google.com": "3F-I",
}

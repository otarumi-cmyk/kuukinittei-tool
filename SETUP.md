# 空き日程ジェネレーター セットアップ手順

3人のGoogleカレンダーから「明日・明後日・明々後日の中で誰かが空いてる時間帯」をDM用にまとめて出力するツール。

---

## 1. GCP（Google Cloud Platform）側の作業

### 1-1. プロジェクト作成
1. https://console.cloud.google.com/ にアクセス
2. 上部のプロジェクト選択 → 「新しいプロジェクト」
3. 適当な名前（例: `calendar-availability-tool`）で作成

### 1-2. Google Calendar API を有効化
1. 左メニュー → 「APIとサービス」→「ライブラリ」
2. 「Google Calendar API」を検索 → 「有効にする」

### 1-3. サービスアカウントを作成
1. 左メニュー → 「IAMと管理」→「サービスアカウント」
2. 「サービスアカウントを作成」をクリック
3. 名前: `calendar-reader`（任意） → 作成
4. ロール付与は **スキップでOK**（FreeBusyは委任で動く）
5. 作成完了

### 1-4. JSONキーをダウンロード
1. 作成したサービスアカウントをクリック
2. 「キー」タブ → 「鍵を追加」→「新しい鍵を作成」→ JSON形式
3. ダウンロードされたJSONファイルを `credentials.json` にリネーム
4. このフォルダ（`空き日程ツール/`）の直下に置く

### 1-5. サービスアカウントの「クライアントID」をメモ
1. 同じサービスアカウントの「詳細」タブ
2. 「一意のID」または「Client ID」（数字の長い列）をコピー
   → 次のステップで使う

---

## 2. Google Workspace 管理コンソール側の作業（管理者権限が必要）

### 2-1. ドメイン全体委任を設定
1. https://admin.google.com/ にアクセス（Workspace管理者でログイン）
2. 左メニュー → 「セキュリティ」→「アクセスとデータ管理」→「APIの制御」
3. 「ドメイン全体の委任」→「新しく追加」
4. **クライアントID**: 先ほどメモしたサービスアカウントのID
5. **OAuthスコープ**: 以下を貼り付け
   ```
   https://www.googleapis.com/auth/calendar.readonly
   ```
6. 「承認」をクリック

これでサービスアカウントが、ドメイン内のユーザーに「なりすまして」カレンダーを読めるようになる。

---

## 3. config.py を編集

`config.py` を開き、4箇所書き換える:

```python
IMPERSONATE_USER = "you@your-domain.co.jp"  # ← 自分のWorkspaceメアド
EMAILS = [
    "member1@your-domain.co.jp",            # ← 対象3人のメアド
    "member2@your-domain.co.jp",
    "member3@your-domain.co.jp",
]
```

- `IMPERSONATE_USER` はドメイン内なら誰のメアドでもOK（このユーザーになりすましてAPIを叩く）。自分のメアドが無難。
- `EMAILS` は表示したい3人のカレンダーのメアド。

営業時間（`WORK_START_HOUR`/`WORK_END_HOUR`）や対象日（`DAYS_AHEAD`）も必要なら変更してください。

---

## 4. 起動

ターミナルでこのフォルダに移動して:

```bash
pip install -r requirements.txt
streamlit run app.py
```

ブラウザが自動で開く（http://localhost:8501）→ 「生成」ボタン → コピペ用テキストが表示される。

---

## 出力イメージ

```
【明日 5/19(月)】10:00-16:00
【明後日 5/20(火)】10:00-12:00 / 14:00-22:00
【明々後日 5/21(水)】13:00-22:00
```

そのままインスタDMにペースト可能。

---

## トラブルシュート

- **`FileNotFoundError: credentials.json`**: JSONキーがフォルダ直下にないか、リネーム漏れ。
- **`unauthorized_client` / `invalid_grant`**: ドメイン全体委任の設定漏れ、またはスコープ違い。手順2-1を再確認。
- **特定の人のカレンダーが空っぽに見える**: その人がWorkspaceドメイン外、または「他のユーザーに予定を非公開」設定をしている可能性。Workspaceの管理者設定で「ドメイン内のfree/busy共有」が有効か確認。
- **`HttpError 403`**: Calendar APIがプロジェクトで有効になっていない（手順1-2）、もしくは委任スコープが間違っている。

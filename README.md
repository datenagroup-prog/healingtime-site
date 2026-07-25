# healingtime.jp - 今日の癒やし言葉

「healingtime.jp」を使った完全自動運用メディアのソースコード一式です。
毎日AIが新しい「癒やしの言葉」を1つ生成し、サイトに自動反映します。人の作業なしで運用できる設計ですが、月1回程度の内容チェックをおすすめします(理由は末尾「運用のコツ」参照)。

## サイト構成

```
healingtime-site/
├── data/
│   ├── site_config.json   # サイト名・広告ID・カテゴリ一覧などの設定
│   ├── quotes.json        # 癒やし言葉のデータ本体(日々ここに追記されていく)
│   └── products.json      # 紹介する商品・アフィリエイトリンクの設定
├── templates/              # ページのHTMLテンプレート(Jinja2)
├── static/style.css        # デザイン(ナチュラル・パステル)
├── scripts/
│   ├── generate_quote.py   # AIで今日の言葉を1件生成し quotes.json に追加
│   └── build_site.py       # data + templates から docs/ に静的サイトを生成
├── docs/                    # ビルド済みの静的サイト(GitHub Pagesで公開する実体)
└── .github/workflows/daily-update.yml  # 毎日自動実行するGitHub Actions
```

**docs/ フォルダがそのまま公開用サイトです。** 一度 `python scripts/build_site.py` を実行すれば `docs/` に完成したHTML一式が生成されます(このリポジトリには初回分をすでに生成済みで同梱しています)。

---

## セットアップ手順(初回のみ)

### 1. GitHubアカウント・リポジトリを用意する

1. https://github.com にアクセスし、アカウントをお持ちでなければ「Sign up」から無料登録してください。
2. ログイン後、右上の「+」→「New repository」で新しいリポジトリを作成します(例: `healingtime-site`、Public/Privateどちらでも可)。
3. このフォルダの中身をすべて、そのリポジトリにアップロードしてください。
   - GitHub Desktopアプリを使う、またはブラウザの「Add file → Upload files」でドラッグ&ドロップでもアップロード可能です。
   - Gitコマンドに慣れている場合は次の手順でも構いません。
     ```
     cd healingtime-site
     git init
     git add .
     git commit -m "first commit"
     git branch -M main
     git remote add origin https://github.com/【あなたのユーザー名】/healingtime-site.git
     git push -u origin main
     ```

### 2. GitHub Pagesを有効化する

1. リポジトリの「Settings」→「Pages」を開く
2. 「Build and deployment」→「Source」で **Deploy from a branch** を選択
3. 「Branch」で **main** ブランチ・フォルダを **/docs** に設定して保存

これで `https://【ユーザー名】.github.io/healingtime-site/` のようなURLで一旦公開されます。

### 3. 独自ドメイン healingtime.jp を接続する

ドメインの管理画面(お名前.com、ムームードメイン、Google Domains等、契約されているレジストラの画面)で、以下のDNSレコードを設定してください。

**ルートドメイン(healingtime.jp 本体)を使う場合 → Aレコードを4つ登録**

| ホスト名 | 種別 | 値 |
|---|---|---|
| @ (空欄でも可) | A | 185.199.108.153 |
| @ | A | 185.199.109.153 |
| @ | A | 185.199.110.153 |
| @ | A | 185.199.111.153 |

**www.healingtime.jp も使いたい場合(任意) → CNAMEレコード**

| ホスト名 | 種別 | 値 |
|---|---|---|
| www | CNAME | 【ユーザー名】.github.io |

設定後、GitHubリポジトリの「Settings → Pages → Custom domain」に `healingtime.jp` と入力して保存し、「Enforce HTTPS」にチェックを入れてください(DNS反映まで数時間〜24時間ほどかかることがあります)。

> このリポジトリの `docs/CNAME` には自動的に `healingtime.jp` が書き込まれる設定になっています(`data/site_config.json` の `base_url` を元に `scripts/build_site.py` が生成します)。

### 4. Anthropic APIキーを取得し、GitHub Secretsに登録する

1. https://console.anthropic.com でアカウントを作成し、APIキーを発行します(従量課金制。1日1回・数百文字程度の生成なので月額コストは非常に小さく収まります)。
2. リポジトリの「Settings → Secrets and variables → Actions → New repository secret」を開く
3. Name: `ANTHROPIC_API_KEY`、Secret: 発行したAPIキーを貼り付けて保存

> `scripts/generate_quote.py` はモデルIDに `claude-sonnet-4-5-20250929` を指定しています。Anthropicは古いモデルを順次終了するため、運用開始時・および数ヶ月ごとに https://docs.claude.com/en/docs/about-claude/models で最新のモデルIDを確認し、必要であれば書き換えてください。

### 5. 自動更新を確認する

- `.github/workflows/daily-update.yml` が毎日 **日本時間 00:05** に自動実行され、新しい言葉の生成 → サイトの再構築 → 自動コミット・プッシュ → GitHub Pages再公開、まで無人で行われます。
- リポジトリの「Actions」タブから、手動で今すぐ1回実行して動作確認することもできます(「Run workflow」ボタン)。

---

## 収益化の設定

### Google AdSense

1. サイトが独自ドメインで公開された状態で https://www.google.com/adsense から申請してください(このサイトには審査に必要な「サイトについて」「プライバシーポリシー」「運営者情報」ページを最初から用意しています)。
2. 承認後、発行される パブリッシャーID(`ca-pub-XXXXXXXXXXXXXXXX`)と、広告ユニットごとのスロットIDを取得します。
3. `data/site_config.json` の以下の項目を書き換えてください。
   ```json
   "adsense_client": "ca-pub-XXXXXXXXXXXXXXXX",
   "adsense_slot_top": "1234567890",
   "adsense_slot_mid": "1234567890",
   "adsense_slot_bottom": "1234567890"
   ```
4. 変更をコミット・プッシュすると、次回の自動ビルド(または手動で `python scripts/build_site.py` を実行してプッシュ)で広告枠に実際の広告が表示されるようになります。空欄のままだとダミーの広告枠(点線の四角)が表示されます。

### アフィリエイト

`data/products.json` に商品ごとの情報が入っています。Amazonアソシエイト・楽天アフィリエイト・A8.net等で発行された紹介リンクを `affiliate_url` に入れるだけで、トップページ・各言葉ページの「おすすめアイテム」欄に反映されます。

```json
{
  "id": "aroma-diffuser",
  "name": "おやすみ前のアロマディフューザー",
  "affiliate_url": "https://ここに発行されたアフィリエイトリンクを貼る"
}
```

商品を追加・入れ替えたい場合も、このファイルに項目を増減するだけで反映されます。

---

## ローカルでの動作確認方法

```bash
cd healingtime-site
pip install -r requirements.txt
python scripts/build_site.py
python -m http.server 8000 --directory docs
```

ブラウザで http://localhost:8000 を開くと、公開前のサイトを確認できます。

新しい言葉を手動で1件生成したい場合(APIキーが必要):

```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxx
python scripts/generate_quote.py
python scripts/build_site.py
```

---

## 運用のコツ(正直な注意点)

- 完全自動でも動きますが、AIが生成する文章は月1回程度、`data/quotes.json` をざっと目視チェックすることをおすすめします。特に「効果を保証するような言い回し」になっていないか(景品表示法・薬機法に配慮したトーンを保つため)を確認してください。`scripts/generate_quote.py` のプロンプトで断定表現を避けるよう指示していますが、AI生成である以上100%の保証はできません。
- AdSense審査は「独自ドメインでの安定運用」「一定量のコンテンツ」「プライバシーポリシー等の整備」が重要視されます。このテンプレートは同梱の10件の言葉だけでも申請可能な体裁を整えていますが、1〜2週間ほど自動更新を続けて記事数を増やしてから申請するとより通過しやすくなります。
- X(旧Twitter)やInstagramへの自動投稿は今回のスコープ外にしていますが、`docs/feed.xml`(RSS)が毎日自動更新されるので、Zapier・IFTTT・Make等のノーコードツールと連携すれば「新しい言葉が追加されたら自動でSNS投稿」という拡張も比較的簡単に追加できます。ご希望があれば、この部分の設計も次のステップとしてお手伝いできます。

---

## デザインについて

ご選択いただいた「①ナチュラル・パステル」のトーンでデザインしています。色やフォントを変更したい場合は `static/style.css` の `:root` 内にあるCSS変数(`--bg`, `--accent` など)を書き換えるだけで、サイト全体の配色に反映されます。

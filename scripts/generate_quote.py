#!/usr/bin/env python3
"""
「今日の癒やし言葉」自動生成スクリプト

Anthropic API (Claude) を使って新しい癒やしの言葉を1件生成し、
data/quotes.json に追記します。既にその日付のデータがあれば何もしません(冪等)。

環境変数:
    ANTHROPIC_API_KEY  - 必須。Anthropic Console で発行したAPIキー
    TARGET_DATE        - 任意。YYYY-MM-DD形式。未指定なら日本時間の「今日」を使用

使い方:
    python scripts/generate_quote.py
"""
import json
import os
import re
import sys
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
QUOTES_PATH = DATA_DIR / "quotes.json"
CONFIG_PATH = DATA_DIR / "site_config.json"

JST = datetime.timezone(datetime.timedelta(hours=9))


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def target_date():
    env_date = os.environ.get("TARGET_DATE")
    if env_date:
        return env_date
    return datetime.datetime.now(tz=JST).date().isoformat()


def build_prompt(categories, recent_quotes):
    recent_text = "\n".join(f"- {q['quote'].replace(chr(10), ' / ')}" for q in recent_quotes[-15:])
    categories_text = "、".join(categories)
    return f"""あなたは「healingtime.jp」という癒やし系メディアの編集者です。
毎日1つ、読者の心が少し軽くなるような短い「今日の癒やし言葉」を作成してください。

# 条件
- quote: 15〜30文字程度、2行構成(改行は \\n を使う)。詩的でやさしい日本語。決めつけや命令口調は避け、そっと寄り添うトーン。
- description: 80〜120文字程度。quoteの内容を優しく補足する一文。断定的な健康・医療・法律・投資等の効果を保証する表現は禁止。個人の感想・寄り添いの範囲に留める。
- category: 次の候補から最も合うものを1つだけ選ぶ: {categories_text}
- 直近の言葉と内容や言い回しが重複しないこと。

# 直近の言葉(重複回避のため参考)
{recent_text if recent_text else "(まだデータがありません)"}

# 出力形式
以下のJSON形式のみを出力してください。前後に説明文やコードブロック記法は付けないでください。
{{"quote": "...", "description": "...", "category": "..."}}
"""


def call_claude(prompt):
    try:
        import anthropic
    except ImportError:
        sys.exit("anthropic パッケージが見つかりません。`pip install -r requirements.txt` を実行してください。")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("環境変数 ANTHROPIC_API_KEY が設定されていません。GitHub Secrets に登録してください。")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def parse_response(text, categories):
    # ```json ... ``` のようなコードフェンスが付いた場合に備えて除去
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    data = json.loads(cleaned)

    quote = data["quote"].strip()
    description = data["description"].strip()
    category = data.get("category", "").strip()
    if category not in categories:
        category = categories[0]
    return quote, description, category


def main():
    config = load_json(CONFIG_PATH)
    categories = config.get("categories", ["自分を大切に"])
    quotes = load_json(QUOTES_PATH)

    date_str = target_date()
    if any(q["date"] == date_str for q in quotes):
        print(f"{date_str} の言葉は既に存在します。生成をスキップします。")
        return

    prompt = build_prompt(categories, quotes)
    raw = call_claude(prompt)

    try:
        quote, description, category = parse_response(raw, categories)
    except Exception as e:
        sys.exit(f"AIの応答をJSONとして解釈できませんでした: {e}\n---\n{raw}")

    quotes.append(
        {
            "date": date_str,
            "category": category,
            "quote": quote,
            "description": description,
        }
    )
    quotes.sort(key=lambda q: q["date"])
    save_json(QUOTES_PATH, quotes)
    print(f"{date_str} の新しい癒やし言葉を追加しました: {quote!r} ({category})")


if __name__ == "__main__":
    main()

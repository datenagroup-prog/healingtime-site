#!/usr/bin/env python3
"""
healingtime.jp サイトビルドスクリプト

data/*.json のデータと templates/*.html を元に、
静的サイト一式を docs/ ディレクトリに生成します。
GitHub Pages は「main ブランチの /docs フォルダ」から配信する設定を想定しています。

使い方:
    python scripts/build_site.py
"""
import json
import shutil
import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
OUT_DIR = ROOT / "docs"

WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]


def load_json(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def date_ja(date_str):
    d = datetime.date.fromisoformat(date_str)
    return f"{d.year}年{d.month}月{d.day}日（{WEEKDAYS_JA[d.weekday()]}）"


def enrich_quotes(quotes, category_to_slug=None):
    category_to_slug = category_to_slug or {}
    quotes = sorted(quotes, key=lambda q: q["date"])
    for q in quotes:
        q["date_ja"] = date_ja(q["date"])
        q["quote_oneline"] = q["quote"].replace("\n", "　")
        q["theme_slug"] = category_to_slug.get(q["category"], "")
    return quotes


def build():
    site = load_json("site_config.json")
    products = load_json("products.json")
    themes = load_json("themes.json")
    category_to_slug = {t["category"]: t["slug"] for t in themes}
    quotes = enrich_quotes(load_json("quotes.json"), category_to_slug)

    if not quotes:
        raise SystemExit("data/quotes.json が空です。先に scripts/generate_quote.py 等で言葉を追加してください。")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    current_year = datetime.date.today().year
    common_ctx = {
        "site": site,
        "current_year": current_year,
        "categories": site.get("categories", []),
    }

    # reset output dir (keep nothing stale)
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)
    (OUT_DIR / "quotes").mkdir(parents=True)
    (OUT_DIR / "archive").mkdir(parents=True)
    (OUT_DIR / "theme").mkdir(parents=True)

    # static

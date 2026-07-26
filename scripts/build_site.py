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


def enrich_quotes(quotes):
    quotes = sorted(quotes, key=lambda q: q["date"])
    for q in quotes:
        q["date_ja"] = date_ja(q["date"])
        q["quote_oneline"] = q["quote"].replace("\n", "　")
    return quotes


def build():
    site = load_json("site_config.json")
    products = load_json("products.json")
    quotes = enrich_quotes(load_json("quotes.json"))

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

    # static assets
    for asset in ["style.css", "favicon.ico", "favicon.svg", "apple-touch-icon.png"]:
           src = STATIC_DIR / asset
           if src.exists():
               shutil.copy(src, OUT_DIR / asset)
       (OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")

    # custom domain (GitHub Pages)
    base_url = site.get("base_url", "")
    if base_url:
        domain = base_url.replace("https://", "").replace("http://", "").strip("/")
        (OUT_DIR / "CNAME").write_text(domain + "\n", encoding="utf-8")

    latest = quotes[-1]
    recent = list(reversed(quotes[:-1]))[:6] or list(reversed(quotes))[:6]

    # index.html
    tpl = env.get_template("index.html")
    (OUT_DIR / "index.html").write_text(
        tpl.render(latest=latest, recent=recent, products=products, **common_ctx),
        encoding="utf-8",
    )

    # archive/index.html
    tpl = env.get_template("archive.html")
    (OUT_DIR / "archive" / "index.html").write_text(
        tpl.render(quotes=list(reversed(quotes)), **common_ctx),
        encoding="utf-8",
    )

    # individual quote pages
    tpl = env.get_template("quote.html")
    for i, q in enumerate(quotes):
        prev_q = quotes[i - 1] if i > 0 else None
        next_q = quotes[i + 1] if i < len(quotes) - 1 else None
        related = [r for r in quotes if r["category"] == q["category"] and r["date"] != q["date"]]
        related = list(reversed(related))[:3]
        html = tpl.render(
            q=q, prev_q=prev_q, next_q=next_q, related=related, products=products, **common_ctx
        )
        (OUT_DIR / "quotes" / f"{q['date']}.html").write_text(html, encoding="utf-8")

    # static prose pages
    for name in ["about.html", "privacy.html", "contact.html"]:
        tpl = env.get_template(name)
        (OUT_DIR / name).write_text(tpl.render(**common_ctx), encoding="utf-8")

    # robots.txt
    (OUT_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n", encoding="utf-8"
    )

    # sitemap.xml
    urls = ["/", "/archive/", "/about.html", "/privacy.html", "/contact.html"]
    urls += [f"/quotes/{q['date']}.html" for q in quotes]
    sitemap_items = "\n".join(
        f"  <url><loc>{escape(base_url + u)}</loc></url>" for u in urls
    )
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{sitemap_items}\n"
        "</urlset>\n"
    )
    (OUT_DIR / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")

    # feed.xml (簡易RSS。SNS自動投稿ツールや検索エンジンへの新着通知にも使えます)
    feed_items = "\n".join(
        f"""  <item>
    <title>{escape(q['quote_oneline'])}</title>
    <link>{escape(base_url + '/quotes/' + q['date'] + '.html')}</link>
    <guid>{escape(base_url + '/quotes/' + q['date'] + '.html')}</guid>
    <pubDate>{q['date']}T00:00:00+09:00</pubDate>
    <description>{escape(q['description'])}</description>
  </item>"""
        for q in list(reversed(quotes))[:20]
    )
    feed_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>\n'
        f"  <title>{escape(site['site_name_ja'])}</title>\n"
        f"  <link>{escape(base_url)}</link>\n"
        f"  <description>{escape(site['description'])}</description>\n"
        f"{feed_items}\n"
        "</channel></rss>\n"
    )
    (OUT_DIR / "feed.xml").write_text(feed_xml, encoding="utf-8")

    print(f"ビルド完了: {len(quotes)} 件の言葉を {OUT_DIR} に生成しました。")
    print(f"最新: {latest['date']} - {latest['quote_oneline']}")


if __name__ == "__main__":
    build()

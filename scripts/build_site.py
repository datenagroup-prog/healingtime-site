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

    columns = load_json("columns.json")
    columns = sorted(columns, key=lambda c: c["date"], reverse=True)
    for c in columns:
        c["date_ja"] = date_ja(c["date"])

    if not quotes:
        raise SystemExit("data/quotes.json が空です。先に scripts/generate_quote.py 等で言葉を追加してください。")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)
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
    (OUT_DIR / "column").mkdir(parents=True)

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
        tpl.render(latest=latest, recent=recent, products=products, themes=themes, columns=columns[:4], **common_ctx),
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

    # theme collection pages (テーマ別まとめページ) — カテゴリごとのSEO向けまとめページ
    tpl = env.get_template("theme.html")
    for t in themes:
        t_quotes = list(reversed([q for q in quotes if q["category"] == t["category"]]))
        other_themes = [ot for ot in themes if ot["slug"] != t["slug"]]
        related_columns = [c for c in columns if c.get("related_theme_slug") == t["slug"]]
        html = tpl.render(
            theme=t, quotes=t_quotes, other_themes=other_themes, products=products,
            related_columns=related_columns, **common_ctx
        )
        page_dir = OUT_DIR / "theme" / t["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(html, encoding="utf-8")

    # theme hub page (テーマから探す)
    tpl = env.get_template("theme_index.html")
    (OUT_DIR / "theme" / "index.html").write_text(
        tpl.render(themes=themes, **common_ctx), encoding="utf-8"
    )

    # column articles (お役立ちコラム記事)
    tpl = env.get_template("column.html")
    for c in columns:
        related_theme = next((t for t in themes if t["slug"] == c.get("related_theme_slug")), None)
        other_columns = [oc for oc in columns if oc["slug"] != c["slug"]][:4]
        html = tpl.render(
            column=c, related_theme=related_theme, other_columns=other_columns,
            products=products, **common_ctx
        )
        page_dir = OUT_DIR / "column" / c["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(html, encoding="utf-8")

    # column hub page (お役立ちコラム一覧)
    tpl = env.get_template("column_index.html")
    (OUT_DIR / "column" / "index.html").write_text(
        tpl.render(columns=columns, **common_ctx), encoding="utf-8"
    )

    # static prose pages
    for name in ["about.html", "privacy.html", "contact.html"]:
        tpl = env.get_template(name)
        (OUT_DIR / name).write_text(tpl.render(**common_ctx), encoding="utf-8")

    # contact form "thank you" page
    tpl = env.get_template("thanks.html")
    (OUT_DIR / "contact-thanks.html").write_text(tpl.render(**common_ctx), encoding="utf-8")

    # robots.txt
    (OUT_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n", encoding="utf-8"
    )

    # sitemap.xml
    urls = ["/", "/archive/", "/theme/", "/column/", "/about.html", "/privacy.html", "/contact.html"]
    urls += [f"/quotes/{q['date']}.html" for q in quotes]
    urls += [f"/theme/{t['slug']}/" for t in themes]
    urls += [f"/column/{c['slug']}/" for c in columns]
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

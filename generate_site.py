from datetime import datetime
from html import escape
from pathlib import Path
import re

import requests


API_URL = "https://dctsports.substack.com/api/v1/posts"
PUBLICATION_URL = "https://dctsports.substack.com"
OUTPUT_FILE = Path("index.html")
PAGE_SIZE = 25


def remove_html(value: str) -> str:
    """Convert HTML into plain text."""
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def shorten(value: str, length: int = 240) -> str:
    """Shorten text without cutting a word in half."""
    if len(value) <= length:
        return value

    shortened = value[:length].rsplit(" ", 1)[0]
    return shortened + "…"


def parse_date(value: str):
    """Convert a Substack date into a datetime."""
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_all_posts():
    """Retrieve every published post from Substack."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 ThroughlineArticleArchive/1.0",
            "Accept": "application/json",
        }
    )

    posts = []
    offset = 0

    while True:
        response = session.get(
            API_URL,
            params={
                "limit": PAGE_SIZE,
                "offset": offset,
            },
            timeout=30,
        )
        response.raise_for_status()

        batch = response.json()

        if not isinstance(batch, list):
            raise RuntimeError("Substack returned an unexpected response.")

        if not batch:
            break

        posts.extend(batch)
        offset += len(batch)

        if len(batch) < PAGE_SIZE:
            break

    return posts


posts = fetch_all_posts()

posts.sort(
    key=lambda post: parse_date(
        post.get("post_date")
        or post.get("published_at")
        or post.get("publication_date")
        or ""
    )
    or datetime.min,
    reverse=True,
)

articles = []

for post in posts:
    title = escape(post.get("title") or "Untitled")

    link = (
        post.get("canonical_url")
        or post.get("post_url")
        or post.get("url")
    )

    if not link:
        slug = post.get("slug", "")
        link = f"{PUBLICATION_URL}/p/{slug}" if slug else PUBLICATION_URL

    link = escape(link, quote=True)

    published = parse_date(
        post.get("post_date")
        or post.get("published_at")
        or post.get("publication_date")
        or ""
    )

    if published:
        publication_date = published.strftime("%B %d, %Y").replace(" 0", " ")
    else:
        publication_date = ""

    raw_summary = (
        post.get("subtitle")
        or post.get("description")
        or post.get("truncated_body_text")
        or ""
    )

    summary = escape(shorten(remove_html(raw_summary)))

    articles.append(
        f"""
        <article class="article-card">
            <p class="date">{publication_date}</p>
            <h2><a href="{link}" target="_blank" rel="noopener">{title}</a></h2>
            <p>{summary}</p>
            <a class="read-more" href="{link}" target="_blank" rel="noopener">
                Read on Substack
            </a>
        </article>
        """
    )

article_html = "\n".join(articles)

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Through Line</title>
    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: #f7f7f5;
            color: #202020;
            font-family: Georgia, "Times New Roman", serif;
            line-height: 1.6;
        }}

        header {{
            padding: 64px 24px 42px;
            text-align: center;
            background: white;
            border-bottom: 1px solid #ddddda;
        }}

        header h1 {{
            margin: 0;
            font-size: clamp(42px, 8vw, 72px);
            line-height: 1;
        }}

        header p {{
            margin: 18px 0 0;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 18px;
            letter-spacing: 0.04em;
        }}

        main {{
            width: min(900px, calc(100% - 40px));
            margin: 48px auto 80px;
        }}

        .article-card {{
            margin-bottom: 24px;
            padding: 30px;
            background: white;
            border: 1px solid #ddddda;
            border-radius: 6px;
        }}

        .article-card h2 {{
            margin: 5px 0 12px;
            font-size: 30px;
            line-height: 1.2;
        }}

        .article-card h2 a {{
            color: #202020;
            text-decoration: none;
        }}

        .article-card h2 a:hover {{
            text-decoration: underline;
        }}

        .date {{
            margin: 0;
            color: #666;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}

        .read-more {{
            display: inline-block;
            margin-top: 6px;
            color: #202020;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
        }}

        footer {{
            padding: 30px 20px;
            text-align: center;
            color: #666;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <header>
        <h1>The Through Line</h1>
        <p>Sports. Media. Pop Culture.</p>
    </header>

    <main>
        {article_html}
    </main>

    <footer>
        Articles by David Tratner
    </footer>
</body>
</html>
"""

OUTPUT_FILE.write_text(page, encoding="utf-8")

print(f"Created {OUTPUT_FILE} with {len(articles)} articles.")
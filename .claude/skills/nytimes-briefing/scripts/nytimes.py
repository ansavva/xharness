# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "httpx==0.27.0",
# ]
# ///
"""NYTimes API skill — morning briefing, top stories, article search, and most popular."""
import argparse
import os
import sys
from datetime import datetime

BASE_URL = "https://api.nytimes.com/svc"

VALID_SECTIONS = [
    "arts", "automobiles", "books", "business", "fashion", "food", "health",
    "home", "insider", "magazine", "movies", "nyregion", "obituaries", "opinion",
    "politics", "realestate", "science", "sports", "sundayreview", "technology",
    "theater", "t-magazine", "travel", "upshot", "us", "world",
]

DEFAULT_BRIEFING_SECTIONS = "home,us,world,business,technology,science,health"


def get_api_key() -> str:
    key = os.environ.get("NYT_API_KEY")
    if not key:
        print("Error: NYT_API_KEY environment variable is not set.", file=sys.stderr)
        print("Register for a free key at https://developer.nytimes.com/", file=sys.stderr)
        sys.exit(1)
    return key


def fetch(url: str) -> dict:
    import httpx
    try:
        resp = httpx.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        print(f"Error: NYTimes API returned {e.response.status_code}.", file=sys.stderr)
        if e.response.status_code == 401:
            print("Check that your NYT_API_KEY is valid.", file=sys.stderr)
        elif e.response.status_code == 429:
            print("Rate limit exceeded. Wait a moment and try again.", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)


def get_top_stories(section: str, api_key: str, n: int) -> list[dict]:
    url = f"{BASE_URL}/topstories/v2/{section}.json?api-key={api_key}"
    data = fetch(url)
    return data.get("results", [])[:n]


def get_most_popular(period: int, api_key: str, n: int) -> list[dict]:
    url = f"{BASE_URL}/mostpopular/v2/viewed/{period}.json?api-key={api_key}"
    data = fetch(url)
    return data.get("results", [])[:n]


def get_search_results(query: str, api_key: str, n: int) -> list[dict]:
    import urllib.parse
    q = urllib.parse.quote_plus(query)
    url = f"{BASE_URL}/search/v2/articlesearch.json?q={q}&api-key={api_key}"
    data = fetch(url)
    return data.get("response", {}).get("docs", [])[:n]


def format_top_article(article: dict, idx: int) -> str:
    title = article.get("title", "").strip() or "(no title)"
    abstract = article.get("abstract", "").strip()
    byline = article.get("byline", "").strip()
    url = article.get("url", "").strip()

    lines = [f"{idx}. **{title}**"]
    if abstract and abstract != title:
        lines.append(f"   {abstract}")
    if byline:
        lines.append(f"   _{byline}_")
    if url:
        lines.append(f"   {url}")
    return "\n".join(lines)


def format_search_article(article: dict, idx: int) -> str:
    headline = article.get("headline", {}).get("main", "").strip() or "(no title)"
    abstract = article.get("abstract", "").strip()
    byline = article.get("byline", {}).get("original", "").strip()
    web_url = article.get("web_url", "").strip()
    pub_date = article.get("pub_date", "")[:10]

    header = f"{idx}. **{headline}**"
    if pub_date:
        header += f" ({pub_date})"
    lines = [header]
    if abstract:
        lines.append(f"   {abstract}")
    if byline:
        lines.append(f"   _{byline}_")
    if web_url:
        lines.append(f"   {web_url}")
    return "\n".join(lines)


def cmd_briefing(args, api_key: str) -> None:
    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    n = args.top_n

    lines = [
        f"# Morning Briefing — {datetime.now().strftime('%A, %B %d, %Y')}",
        "",
    ]

    for section in sections:
        articles = get_top_stories(section, api_key, n)
        if not articles:
            continue
        label = section.replace("-", " ").title()
        lines.append(f"## {label}")
        lines.append("")
        for i, article in enumerate(articles, 1):
            lines.append(format_top_article(article, i))
            lines.append("")

    if args.popular:
        articles = get_most_popular(1, api_key, n)
        if articles:
            lines.append("## Most Read Today")
            lines.append("")
            for i, article in enumerate(articles, 1):
                lines.append(format_top_article(article, i))
                lines.append("")

    print("\n".join(lines))


def cmd_top(args, api_key: str) -> None:
    section = args.section.lower()
    articles = get_top_stories(section, api_key, args.top_n)
    if not articles:
        print(f"No articles found for section '{section}'.")
        return
    label = section.replace("-", " ").title()
    print(f"## Top Stories — {label}\n")
    for i, article in enumerate(articles, 1):
        print(format_top_article(article, i))
        print()


def cmd_search(args, api_key: str) -> None:
    query = " ".join(args.query)
    articles = get_search_results(query, api_key, args.top_n)
    if not articles:
        print(f"No results found for '{query}'.")
        return
    print(f"## Search Results — \"{query}\"\n")
    for i, article in enumerate(articles, 1):
        print(format_search_article(article, i))
        print()


def cmd_popular(args, api_key: str) -> None:
    period = args.period
    articles = get_most_popular(period, api_key, args.top_n)
    if not articles:
        print("No popular articles found.")
        return
    period_label = {1: "Today", 7: "This Week", 30: "This Month"}[period]
    print(f"## Most Viewed — {period_label}\n")
    for i, article in enumerate(articles, 1):
        print(format_top_article(article, i))
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NYTimes API skill — briefing, top stories, search, and popular articles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # briefing
    p = sub.add_parser("briefing", help="Generate a morning news briefing")
    p.add_argument(
        "--sections", default=DEFAULT_BRIEFING_SECTIONS,
        help=f"Comma-separated sections (default: {DEFAULT_BRIEFING_SECTIONS})",
    )
    p.add_argument("--top-n", type=int, default=5, metavar="N", help="Articles per section (default: 5)")
    p.add_argument("--popular", action="store_true", help="Append most-read articles")

    # top
    p = sub.add_parser("top", help="Top stories from a section")
    p.add_argument("section", help=f"Section name (e.g. {', '.join(VALID_SECTIONS[:6])}, ...)")
    p.add_argument("--top-n", type=int, default=10, metavar="N", help="Number of articles (default: 10)")

    # search
    p = sub.add_parser("search", help="Search NYTimes article archives")
    p.add_argument("query", nargs="+", help="Search keywords")
    p.add_argument("--top-n", type=int, default=10, metavar="N", help="Number of results (default: 10)")

    # popular
    p = sub.add_parser("popular", help="Most-viewed articles")
    p.add_argument("--period", type=int, default=1, choices=[1, 7, 30], metavar="DAYS", help="1, 7, or 30 days (default: 1)")
    p.add_argument("--top-n", type=int, default=10, metavar="N", help="Number of articles (default: 10)")

    args = parser.parse_args()
    api_key = get_api_key()

    {"briefing": cmd_briefing, "top": cmd_top, "search": cmd_search, "popular": cmd_popular}[args.command](args, api_key)


if __name__ == "__main__":
    main()

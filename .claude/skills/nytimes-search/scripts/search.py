# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "httpx==0.27.0",
# ]
# ///
"""NYTimes Article Search — keyword search of the NYTimes archive."""
import argparse
import os
import sys
import urllib.parse

BASE_URL = "https://api.nytimes.com/svc"


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


def search_articles(query: str, api_key: str, n: int, sort: str, begin_date: str | None, end_date: str | None) -> list[dict]:
    q = urllib.parse.quote_plus(query)
    url = f"{BASE_URL}/search/v2/articlesearch.json?q={q}&sort={sort}&api-key={api_key}"
    if begin_date:
        url += f"&begin_date={begin_date}"
    if end_date:
        url += f"&end_date={end_date}"
    data = fetch(url)
    return data.get("response", {}).get("docs", [])[:n]


def format_article(article: dict, idx: int) -> str:
    headline = article.get("headline", {}).get("main", "").strip() or "(no title)"
    abstract = article.get("abstract", "").strip()
    byline = article.get("byline", {}).get("original", "").strip()
    web_url = article.get("web_url", "").strip()
    pub_date = article.get("pub_date", "")[:10]
    section = article.get("section_name", "").strip()

    header = f"{idx}. **{headline}**"
    if pub_date:
        header += f" ({pub_date})"
    if section:
        header += f" · _{section}_"
    lines = [header]
    if abstract:
        lines.append(f"   {abstract}")
    if byline:
        lines.append(f"   {byline}")
    if web_url:
        lines.append(f"   {web_url}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search NYTimes article archives by keyword",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="+", help="Search keywords (e.g. climate change)")
    parser.add_argument(
        "--top-n", type=int, default=10, metavar="N",
        help="Number of results to show (default: 10)",
    )
    parser.add_argument(
        "--sort", default="relevance", choices=["relevance", "newest", "oldest"],
        help="Sort order: relevance, newest, oldest (default: relevance)",
    )
    parser.add_argument(
        "--from", dest="begin_date", metavar="YYYYMMDD",
        help="Earliest publication date filter",
    )
    parser.add_argument(
        "--to", dest="end_date", metavar="YYYYMMDD",
        help="Latest publication date filter",
    )

    args = parser.parse_args()
    api_key = get_api_key()
    query = " ".join(args.query)

    articles = search_articles(query, api_key, args.top_n, args.sort, args.begin_date, args.end_date)
    if not articles:
        print(f'No results found for "{query}".')
        return

    print(f'## NYTimes Search — "{query}"\n')
    for i, article in enumerate(articles, 1):
        print(format_article(article, i))
        print()


if __name__ == "__main__":
    main()

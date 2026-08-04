---
name: nytimes-search
description: Search the NYTimes article archive by keyword, with optional date range and sort order
argument-hint: "<query> [--top-n N] [--sort relevance|newest|oldest] [--from YYYYMMDD] [--to YYYYMMDD]"
allowed-tools:
  - Bash
---

Search the NYTimes article archive using the query in $ARGUMENTS.

Requires the `NYT_API_KEY` environment variable. Get a free key at https://developer.nytimes.com/.

Run from the repo root:

```bash
uv run .claude/skills/nytimes-search/scripts/search.py <query> [--top-n N] [--sort relevance|newest|oldest] [--from YYYYMMDD] [--to YYYYMMDD]
```

Arguments:
- `<query>` — one or more keywords (e.g. `climate change`, `artificial intelligence`)
- `--top-n N` — number of results to return (default: 10)
- `--sort` — sort order: `relevance` (default), `newest`, or `oldest`
- `--from YYYYMMDD` — only include articles published on or after this date
- `--to YYYYMMDD` — only include articles published on or before this date

Each result shows: headline, publication date, section, abstract, byline, and URL.

Print the results directly in the conversation. If `NYT_API_KEY` is missing, tell the user to register at https://developer.nytimes.com/ and set the env var. If `uv` is not installed, tell the user to run `brew install uv`.

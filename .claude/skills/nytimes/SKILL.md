---
name: nytimes
description: Search the NYTimes API — morning briefing, top stories by section, article search, and most popular
argument-hint: "briefing | top <section> | search <query> | popular"
allowed-tools:
  - Bash
---

Dispatch to the NYTimes API skill based on the sub-command in $ARGUMENTS.

Requires the `NYT_API_KEY` environment variable. Get a free key at https://developer.nytimes.com/.

All sub-commands are run from the repo root:

**briefing** — Generate a morning news briefing across multiple sections:
```bash
uv run .claude/skills/nytimes/scripts/nytimes.py briefing [--sections home,us,world,business,technology,science,health] [--top-n N] [--popular]
```
- `--sections` — comma-separated list of NYT sections (default: home,us,world,business,technology,science,health)
- `--top-n N` — number of articles per section (default: 5)
- `--popular` — append most-read articles at the end

**top** — Get top stories from a specific section:
```bash
uv run .claude/skills/nytimes/scripts/nytimes.py top <section> [--top-n N]
```
- `<section>` — e.g. home, us, world, business, technology, science, health, sports, arts, books, food, travel, opinion, politics, movies
- `--top-n N` — number of articles to show (default: 10)

**search** — Search NYTimes article archives by keyword:
```bash
uv run .claude/skills/nytimes/scripts/nytimes.py search <query> [--top-n N]
```
- `<query>` — one or more keywords (e.g. `climate change`)
- `--top-n N` — number of results to show (default: 10)

**popular** — Show the most-viewed NYTimes articles:
```bash
uv run .claude/skills/nytimes/scripts/nytimes.py popular [--period 1|7|30] [--top-n N]
```
- `--period` — time window in days: 1, 7, or 30 (default: 1)
- `--top-n N` — number of articles to show (default: 10)

Print the output directly in the conversation. If `NYT_API_KEY` is missing, tell the user to register at https://developer.nytimes.com/ and set the env var. If `uv` is not installed, tell the user to run `brew install uv`.

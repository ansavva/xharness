---
name: nytimes-briefing
description: NYTimes morning briefing — daily digest, top stories by section, and most popular articles
argument-hint: "[briefing] | top <section> | popular [--period 1|7|30]"
allowed-tools:
  - Bash
---

Dispatch to the NYTimes briefing skill based on the sub-command in $ARGUMENTS.

Requires the `NYT_API_KEY` environment variable. Get a free key at https://developer.nytimes.com/.

All sub-commands are run from the repo root:

**briefing** (default) — Generate a morning news briefing across multiple sections:
```bash
uv run .claude/skills/nytimes-briefing/scripts/nytimes.py briefing [--sections home,us,world,business,technology,science,health] [--top-n N] [--popular]
```
- `--sections` — comma-separated list of NYT sections (default: home,us,world,business,technology,science,health)
- `--top-n N` — number of articles per section (default: 5)
- `--popular` — append most-read articles at the end

**top** — Get top stories from a specific section:
```bash
uv run .claude/skills/nytimes-briefing/scripts/nytimes.py top <section> [--top-n N]
```
- `<section>` — e.g. home, us, world, business, technology, science, health, sports, arts, books, food, travel, opinion, politics, movies
- `--top-n N` — number of articles (default: 10)

**popular** — Show the most-viewed NYTimes articles:
```bash
uv run .claude/skills/nytimes-briefing/scripts/nytimes.py popular [--period 1|7|30] [--top-n N]
```
- `--period` — time window in days: 1, 7, or 30 (default: 1)
- `--top-n N` — number of articles (default: 10)

Print the output directly in the conversation. If `NYT_API_KEY` is missing, tell the user to register at https://developer.nytimes.com/ and set the env var. If `uv` is not installed, tell the user to run `brew install uv`.

If no sub-command is given, default to running `briefing` with default options.

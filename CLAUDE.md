# xharness — Claude Code Tool Harness

A personal collection of Python tools callable as Claude Code skills.
Skills live in `.claude/skills/`. Scripts use `uv` with PEP 723 inline
metadata — each script declares its own dependencies, no shared venv.

---

## Repo layout

```
xharness/
├── .claude/
│   ├── settings.json              — pre-approved Bash permissions + SessionStart hook
│   ├── hooks/
│   │   └── session-start.sh       — runs dev-setup on session start
│   └── skills/
│       ├── qr/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── generate.py
│       ├── photos/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       ├── scan.py        — entry point
│       │       ├── cache.py       — SQLite helpers (~/.photo-migrate/photos.db)
│       │       ├── takeout_scanner.py
│       │       └── icloud_scanner.py
│       ├── kindle/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── kindle.py
│       ├── nytimes-briefing/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── nytimes.py     — briefing, top, popular
│       └── nytimes-search/
│           ├── SKILL.md
│           └── scripts/
│               └── search.py      — keyword article search
├── scripts/
│   └── dev-setup.sh               — idempotent prerequisite installer
└── CLAUDE.md
```

---

## One-time setup

```bash
scripts/dev-setup.sh
```

This installs the only hard prerequisite — `uv` — via `brew install uv` if
it's missing, and warms the dependency caches for the cross-platform skills.
It's idempotent, so it's safe to run any time. `uv` then handles Python
versions and dependencies automatically per script.

The script runs automatically at the start of every Claude Code session via
the `SessionStart` hook registered in `.claude/settings.json`, so remote/web
sessions come up ready to use.

External tools required by some skills (installed separately, per platform):
- **Calibre CLI** (`ebook-convert`) — https://calibre-ebook.com — required for `kindle`
- **exiftool** — `brew install exiftool` — required for future photo metadata embedding

API keys required by some skills:
- **NYT_API_KEY** — https://developer.nytimes.com/ — required for `nytimes-briefing` and `nytimes-search` (free tier available)
- **REPLICATE_API_TOKEN** — https://replicate.com/account/api-tokens — optional for `seedance-video`; enables uploading full-resolution reference images. Put keys in a `.env` file at the repo root (copy `.env.example`; `.env` is git-ignored).
- **Google Drive OAuth** (`GOOGLE_DRIVE_CLIENT_ID` / `GOOGLE_DRIVE_CLIENT_SECRET` / `GOOGLE_DRIVE_REFRESH_TOKEN`) — used by the `google-drive` skill (a general Drive layer). `seedance-video` / `fred` build on it: character **reference images and generated videos live in Google Drive**, not in git. Run `google-drive`'s `drive_auth.py` for one-command setup; full steps are in `.env.example`.

---

## Available skills

| Skill     | What it does                                              |
|-----------|-----------------------------------------------------------|
| `qr`      | Generate a QR code PNG from a URL                        |
| `photos`  | Scan Google Takeout or iCloud Photos library into SQLite |
| `kindle`  | Prepare a PDF for Kindle (clean → EPUB → Previewer)      |
| `nytimes-briefing` | Morning briefing, top stories by section, most popular (requires `NYT_API_KEY`) |
| `nytimes-search`   | Keyword article search with date filters and sort order (requires `NYT_API_KEY`) |
| `seedance-video`   | Generate videos with ByteDance Seedance 2.0 via the Replicate MCP (text/image/character → MP4) |
| `fred`             | On-model videos of the "Fred" character; runs on `seedance-video` |
| `google-drive`     | Read/write Google Drive via the REST API (list, upload, download, one-command OAuth) |

---

## How skills call tools

Each entry script declares its own dependencies inline using PEP 723:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = ["qrcode[pil]==8.0"]
# ///
```

Skills invoke them via `uv run`, which builds a cached isolated env on first
use and reuses it on subsequent runs:

```bash
uv run .claude/skills/qr/scripts/generate.py "https://example.com" -o /tmp/qr.png
uv run .claude/skills/photos/scripts/scan.py scan-takeout /path/to/takeout
uv run .claude/skills/kindle/scripts/kindle.py /path/to/book.pdf
uv run .claude/skills/nytimes-briefing/scripts/nytimes.py briefing
uv run .claude/skills/nytimes-search/scripts/search.py "climate change"
```

For multi-file skills (like `photos`), only the entry script needs the
inline metadata — its declared deps are available to all sibling modules
imported during the run.

---

## How to add a new skill

1. Create `.claude/skills/<name>/SKILL.md` with YAML frontmatter and instructions
2. Create the entry script at `.claude/skills/<name>/scripts/<script>.py` with a `# /// script` block declaring its deps
3. If the skill needs new Bash patterns, add them to `.claude/settings.json`
4. Document the new skill in the table above

No central `requirements.txt` or venv to update.

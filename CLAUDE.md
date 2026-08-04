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
│       └── kindle/
│           ├── SKILL.md
│           └── scripts/
│               └── kindle.py
├── scripts/
│   └── dev-setup.sh               — idempotent prerequisite installer
└── CLAUDE.md
```

---

## One-time setup

```bash
scripts/dev-setup.sh
```

This installs the only hard prerequisite — `uv` — if it's missing (via
`brew install uv`, falling back to the official installer when Homebrew
isn't available, e.g. remote/web sessions), and warms the dependency caches
for the cross-platform skills. It's idempotent, so it's safe to run any time.
`uv` then handles Python versions and dependencies automatically per script.

The script runs automatically at the start of every Claude Code session via
the `SessionStart` hook registered in `.claude/settings.json`, so remote/web
sessions come up ready to use.

External tools required by some skills (installed separately, per platform):
- **Calibre CLI** (`ebook-convert`) — https://calibre-ebook.com — required for `kindle`
- **exiftool** — `brew install exiftool` — required for future photo metadata embedding

---

## Available skills

| Skill     | What it does                                              |
|-----------|-----------------------------------------------------------|
| `qr`      | Generate a QR code PNG from a URL                        |
| `photos`  | Scan Google Takeout or iCloud Photos library into SQLite |
| `kindle`  | Prepare a PDF for Kindle (clean → EPUB → Previewer)      |

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

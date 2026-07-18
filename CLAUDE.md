# xharness — Claude Code Tool Harness

A personal collection of Python tools callable as Claude Code skills.
Skills live in `.claude/skills/`. Scripts use `uv` with PEP 723 inline
metadata — each script declares its own dependencies, no shared venv.

---

## Repo layout

```
xharness/
├── .claude/
│   ├── settings.json              — pre-approved Bash permissions
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
│       └── wordgen/
│           ├── SKILL.md
│           └── scripts/
│               └── wordgen.py
├── scripts/
│   └── dev-setup.sh               — brew bootstrap (macOS + Linux)
└── CLAUDE.md
```

---

## One-time setup

Run the bootstrap script — it installs everything via Homebrew on both macOS
and Linux, and is idempotent (safe to re-run):

```bash
./scripts/dev-setup.sh            # install everything missing
./scripts/dev-setup.sh --check    # report status only, install nothing
```

It installs:
- **uv** — core; every skill runs its Python via `uv run` (uv provisions Python
  and per-script deps automatically, so nothing else Python-related is needed)
- **exiftool** — for the `photos` skill (metadata read/embed)
- **Calibre** (`ebook-convert`) — for the `kindle` skill; a Homebrew cask on
  macOS, installed via apt on Linux (Homebrew has no Linux calibre formula)

Manual, not scripted: **Kindle Previewer 3** (macOS/Windows only) for the final
`kindle` step — https://www.amazon.com/Kindle-Previewer/b?node=21381691011

Prefer to do it by hand? The minimum is `brew install uv`; `uv` handles Python
versions and dependencies automatically per script.

---

## Available skills

| Skill     | What it does                                              |
|-----------|-----------------------------------------------------------|
| `qr`      | Generate a QR code PNG from a URL                        |
| `photos`  | Scan Google Takeout or iCloud Photos library into SQLite |
| `kindle`  | Prepare a PDF for Kindle (clean → EPUB → Previewer)      |
| `wordgen` | Generate pronounceable pseudowords that sound real but aren't (styles + naming-brief constraints) |

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

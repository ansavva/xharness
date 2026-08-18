# xharness — Claude Code Tool Harness

A personal collection of Python tools callable as Claude Code skills. Skills
live in `.claude/skills/`. Scripts use `uv` with PEP 723 inline metadata — each
script declares its own dependencies, no shared venv, no `requirements.txt`.

> **The studio pipeline is no longer here.** In August 2026 the `s3` and
> `studio-*` skills, the media bucket's Terraform, and every rule that governed
> them moved to `studio/` in the **andreas-services** monorepo, where they now
> sit alongside the web app that browses their output. This repo kept only the
> general-purpose tools below, which have nothing to do with that pipeline.
>
> Do not re-add a studio skill here. If you are looking for characters, runs,
> scenes, movies, Replicate or the `xharness-prod-media-us-east-1` bucket, the
> place is `andreas-services/studio/` — start at its `CLAUDE.md`.

---

## Repo layout

```
xharness/
├── .claude/
│   ├── settings.json              — pre-approved Bash permissions + SessionStart hook
│   ├── hooks/
│   │   └── session-start.sh       — runs dev-setup on session start
│   └── skills/
│       ├── qr/scripts/generate.py
│       ├── photos/scripts/        — scan.py (entry), cache.py, takeout_scanner.py, icloud_scanner.py
│       ├── kindle/scripts/kindle.py
│       ├── nytimes-briefing/scripts/nytimes.py   — briefing, top, popular
│       ├── nytimes-search/scripts/search.py      — keyword article search
│       ├── transcribe/scripts/transcribe.py      — Whisper, runs locally
│       └── google-drive/scripts/                 — drive_auth/common/upload/download.py
├── scripts/
│   └── dev-setup.sh               — idempotent prerequisite installer
├── output/transcripts/            — transcribe output (git-ignored)
├── .env                           — API keys (git-ignored; copy .env.example)
└── CLAUDE.md
```

---

## One-time setup

```bash
scripts/dev-setup.sh
```

Installs the only hard prerequisite — `uv` — via Homebrew if missing, and warms
the dependency caches. Idempotent, and it runs automatically at the start of
every session via the `SessionStart` hook in `.claude/settings.json`.

External tools some skills need:

- **Calibre CLI** (`ebook-convert`) — https://calibre-ebook.com — for `kindle`
- **exiftool** — `brew install exiftool` — for `photos` metadata embedding
- **ffmpeg** — `brew install ffmpeg` — for `transcribe` (Whisper decodes through it)

API keys go in `.env` at the repo root (copy `.env.example`; `.env` is
git-ignored):

- **NYT_API_KEY** — https://developer.nytimes.com/ — for both `nytimes-*` skills
- **GOOGLE_DRIVE_\*** — for `google-drive`; run its `drive_auth.py` to fill them in

---

## Available skills

| Skill | What it does |
|---|---|
| `qr` | Generate a QR code PNG from a URL |
| `photos` | Scan Google Takeout or an iCloud Photos library into SQLite |
| `kindle` | Prepare a PDF for Kindle (clean → EPUB → Previewer) |
| `nytimes-briefing` | Morning briefing, top stories by section, most popular (needs `NYT_API_KEY`) |
| `nytimes-search` | Keyword article search with date filters and sort order (needs `NYT_API_KEY`) |
| `transcribe` | Transcribe a YouTube video or local media file to txt/srt/vtt with OpenAI Whisper, running locally — no API key (needs `ffmpeg`); writes to `output/transcripts/` |
| `google-drive` | Read/write Google Drive via the REST API — list, upload, download, one-command OAuth setup |

`google-drive` was the studio pipeline's original asset store before it moved to
S3. It stays because it is a general-purpose storage layer any task can use, but
nothing here depends on it.

---

## How skills call tools

Every script is standalone and declares its own dependencies inline:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = ["qrcode[pil]==8.0"]
# ///
```

Run one with `uv run --script <path> [args]`. `uv` resolves and caches an
isolated environment per script on first use.

## How to add a new skill

1. Create `.claude/skills/<name>/SKILL.md` with YAML frontmatter and instructions
2. Create the entry script at `.claude/skills/<name>/scripts/<script>.py` with a
   `# /// script` block declaring its deps
3. If the skill needs new Bash patterns, add them to `.claude/settings.json`
4. Add a `prewarm` line to `scripts/dev-setup.sh` if it is an entry point
5. Document it in the table above

No central `requirements.txt` or venv to update.

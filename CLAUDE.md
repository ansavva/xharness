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
│       ├── nytimes-search/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── search.py      — keyword article search
│       ├── studio-video/          — [studio-*] Seedance 2.0 render engine (Replicate MCP)
│       │   ├── SKILL.md
│       │   └── scripts/           — upload_to_replicate.py / img2datauri.py (local-image fallbacks)
│       ├── studio-prompt/         — [studio-*] author Seedance prompts as JSON
│       │   ├── SKILL.md
│       │   └── scripts/build_prompt.py   — assemble + validate; split technical → API params
│       ├── studio-character/      — [studio-*] character CRUD; profiles + refs in S3 (media/<name>/)
│       │   ├── SKILL.md
│       │   ├── templates/profile.md      — blank character bible
│       │   └── scripts/
│       │       ├── character.py          — list/create/show/set-profile/add-refs/refs (+captions; uses s3)
│       │       └── contact_sheet.py      — labeled contact sheet for a character folder (S3 or local)
│       └── s3/
│           ├── SKILL.md
│           └── scripts/
│               ├── s3_common.py   — auth (aws-CLI credential bridge) + helpers
│               ├── s3_upload.py   — local file(s) → media/<folder>/
│               ├── s3_download.py — list / download a media folder
│               └── s3_presign.py  — objects → temporary HTTPS URLs (for Replicate)
├── infra/                         — Terraform: the xharness-assets S3 bucket
│   ├── main.tf variables.tf outputs.tf
│   ├── apply.sh                   — init + apply against an AWS profile
│   ├── README.md
│   └── modules/media-bucket/      — reusable S3 asset-bucket module
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
- **AWS CLI** (`aws`) — `brew install awscli` — required for the `s3` skill (asset store). Sign in with `aws login` (or `aws sso login` / `aws configure`) each session.

API keys required by some skills:
- **NYT_API_KEY** — https://developer.nytimes.com/ — required for `nytimes-briefing` and `nytimes-search` (free tier available)
- **REPLICATE_API_TOKEN** — https://replicate.com/account/api-tokens — optional for `studio-video`; only needed to upload full-resolution *local* reference images (S3-hosted references use presigned URLs and need no token). Put keys in a `.env` file at the repo root (copy `.env.example`; `.env` is git-ignored).

Asset storage (the `s3` skill) uses your **AWS login**, not an API key. The
`studio-*` workflow stores character **profiles, reference images, and generated
videos in S3** (bucket `xharness-assets`, under `media/<name>/`), not in git —
provisioned by Terraform in [`infra/`](infra/README.md). The `google-drive` skill
remains in the repo but is **legacy** (the workflow moved off Drive to S3).

---

## Available skills

| Skill     | What it does                                              |
|-----------|-----------------------------------------------------------|
| `qr`      | Generate a QR code PNG from a URL                        |
| `photos`  | Scan Google Takeout or iCloud Photos library into SQLite |
| `kindle`  | Prepare a PDF for Kindle (clean → EPUB → Previewer)      |
| `nytimes-briefing` | Morning briefing, top stories by section, most popular (requires `NYT_API_KEY`) |
| `nytimes-search`   | Keyword article search with date filters and sort order (requires `NYT_API_KEY`) |
| `studio-video`     | **[studio-*]** Generate videos with ByteDance Seedance 2.0 via the Replicate MCP (text/image/character → MP4); the render engine |
| `studio-prompt`    | **[studio-*]** Author Seedance 2.0 prompts as structured JSON (validates rules, splits technical fields to API params); feeds `studio-video` |
| `studio-character` | **[studio-*]** Manage on-model characters (create/update/list/load) whose bible + reference images live in S3 (`media/<name>/`); characters are data, not skills |
| `s3`               | Read/write the `xharness-assets` S3 bucket (list, upload, download, presign) — the video workflow's asset store |
| `google-drive`     | *Legacy* — Read/write Google Drive via the REST API (superseded by `s3` for the video workflow) |

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
uv run .claude/skills/s3/scripts/s3_presign.py --folder <name>/reference --json
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

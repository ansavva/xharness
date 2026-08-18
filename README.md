# xharness

A personal collection of Python tools callable as Claude Code skills — QR codes,
a photo-library scanner, a PDF-to-Kindle converter, NYTimes briefing and search,
local Whisper transcription, and a Google Drive storage layer.

Each script declares its own dependencies with PEP 723 inline metadata and runs
under `uv`; there is no shared virtualenv. Run `scripts/dev-setup.sh` once (the
session hook does it automatically) and see [CLAUDE.md](CLAUDE.md) for the full
list and setup.

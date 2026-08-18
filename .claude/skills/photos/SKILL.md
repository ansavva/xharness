---
name: photos
description: Scan Google Takeout exports or iCloud Photos library into a local SQLite index
argument-hint: "scan-takeout <path> | scan-icloud [--library <path>] | setup"
allowed-tools:
  - Bash
---

Dispatch to the photos scanner based on the sub-command in $ARGUMENTS.

All sub-commands are run from the repo root:

**scan-takeout** — index a Google Takeout export folder to SQLite (`~/.photo-migrate/photos.db`):
```bash
uv run .claude/skills/photos/scripts/scan.py scan-takeout <path> [--quiet] [--reset]
```
- `<path>` must contain a `Takeout/Google Photos/` subdirectory
- `--reset` wipes and recreates the database before scanning
- `--quiet` suppresses the progress bar

**scan-icloud** — index the local Photos.app library to SQLite (incremental — only new photos since last scan):
```bash
uv run .claude/skills/photos/scripts/scan.py scan-icloud [--library <path>] [--quiet]
```
- `--library` overrides the default location (`~/Pictures/Photos Library.photoslibrary`)

**setup** — print Google Takeout export instructions and check system requirements:
```bash
uv run .claude/skills/photos/scripts/scan.py setup
```

After `scan-takeout` or `scan-icloud`, summarize the stats (indexed / skipped / errors) from the output.
For `setup`, relay requirement check results and highlight any missing dependencies.

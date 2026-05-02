---
name: qr
description: Generate a QR code PNG from a URL
argument-hint: "<url> [--output path.png] [--box-size N] [--border N]"
allowed-tools:
  - Bash
---

Generate a QR code PNG from the URL provided in $ARGUMENTS.

Run from the repo root:

```bash
uv run .claude/skills/qr/scripts/generate.py <url> [--output <path>] [--box-size <N>] [--border <N>]
```

Arguments:
- `url` — required, the URL to encode
- `--output` — output file path (default: `qr_code.png` in the current directory)
- `--box-size` — pixel size per QR module (default: 10)
- `--border` — border width in QR modules (default: 4)

Report the output file path on success. If `uv` is not installed, tell the user to run `brew install uv`.

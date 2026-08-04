---
name: google-drive
description: Read from and write to Google Drive via the Drive REST API — list a folder, upload local files into a folder path, download files to disk, and run a one-command OAuth setup. A general storage layer usable by any skill or task; other skills (e.g. seedance-video / fred) call these scripts to keep large assets in Drive instead of git. Use when the user wants to store, fetch, sync, back up, or list files in Google Drive, or needs to set up / refresh Google Drive credentials. Bytes move disk↔Drive directly, so nothing is base64-inlined into the agent context.
---

# Google Drive skill

A scriptable Google Drive layer. Files move **disk ↔ Drive directly** (never
base64-inlined into the agent context, the way the Drive MCP would), so it
handles full-resolution images and multi-MB videos cheaply. It is
general-purpose — any skill or task can call these scripts.

Everything is stored under a single **root folder** in the credential owner's
*My Drive* (default `xharness`, override with `GOOGLE_DRIVE_ROOT_FOLDER`). Paths
are slash-separated *under* that root, e.g. `fred/reference`.

## Setup (one time)

Credentials come from a `.env` file at the repo root (copy `.env.example`). The
Drive API needs a user OAuth credential; the fields are
`GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, and
`GOOGLE_DRIVE_REFRESH_TOKEN` (or a short-lived `GOOGLE_DRIVE_ACCESS_TOKEN` for a
quick test). Full console steps are documented in `.env.example`.

**Easiest way to get the refresh token** — once the client ID + secret are in
`.env`, add `http://localhost:8765/` as an Authorized redirect URI on the OAuth
client, then run:

```bash
uv run .claude/skills/google-drive/scripts/drive_auth.py
```

It opens the Google consent screen, captures the redirect on localhost,
exchanges the code, **writes `GOOGLE_DRIVE_REFRESH_TOKEN` back into `.env`**, and
verifies access. Re-run it whenever the token expires (OAuth *Testing*-mode
refresh tokens lapse after 7 days — click "Publish app" on the consent screen to
avoid that).

## Scripts

All are `uv` scripts (PEP 723; dependency `requests`) under
`.claude/skills/google-drive/scripts/`. Each accepts `--env PATH` to point at a
specific `.env`.

| Script | Purpose |
|---|---|
| `drive_auth.py` | One-command loopback OAuth → writes `GOOGLE_DRIVE_REFRESH_TOKEN` to `.env`. |
| `drive_upload.py` | Upload local file(s) into a Drive folder path (created if missing); same-named files update in place. Prints `webViewLink`s. |
| `drive_download.py` | List a Drive folder, or download named files / everything to a local dir. |
| `drive_common.py` | Shared auth + REST helpers (imported by the others; not run directly). |

```bash
GD=.claude/skills/google-drive/scripts

# List a folder
uv run $GD/drive_download.py --folder fred/reference --list

# Download everything in a folder to a temp dir (JSON map of name -> local path)
uv run $GD/drive_download.py --folder fred/reference --all --dest /tmp/refs --json

# Upload files into a folder path (folder auto-created)
uv run $GD/drive_upload.py --folder fred/output output/fred/clip.mp4

# One-command OAuth (writes the refresh token to .env)
uv run $GD/drive_auth.py
```

## Notes

- Auth resolution order: `GOOGLE_DRIVE_ACCESS_TOKEN` (if present) → the
  client/secret/refresh-token trio (refreshed to an access token per run).
- Uploads are **idempotent**: a same-named file in the target folder is updated
  in place (new revision), not duplicated.
- Without a credential the scripts fail with a clear, actionable message — they
  never silently no-op.
- `invalid_grant` on any call means the refresh token is missing/expired/placeholder
  → re-run `drive_auth.py`.

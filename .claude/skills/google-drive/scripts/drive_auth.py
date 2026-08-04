#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-auth-oauthlib>=1.2", "requests>=2.31"]
# ///
"""
drive_auth.py — one-command Google Drive OAuth using the standard installed-app
(loopback) flow, then write the credential back into .env.

Uses google-auth-oauthlib's InstalledAppFlow (the same pattern as a typical
get_*_tokens.py): it opens a browser, runs a local loopback server on an
EPHEMERAL port, and exchanges the code — so with a **Desktop app** OAuth client
there is NOTHING to pre-register (Desktop clients permit loopback redirects
automatically). On success it writes GOOGLE_DRIVE_CLIENT_ID / _CLIENT_SECRET /
_REFRESH_TOKEN into .env, so drive_upload.py / drive_download.py (which mint
access tokens from that trio) just work. Re-run whenever the refresh token is
revoked or a Testing-mode token lapses (7 days).

Client credentials come from either (checked in this order):
  1. --credentials PATH, or a `credentials.json` found in the current dir / repo
     root / this script's dir — the OAuth client JSON downloaded from
     Google Cloud Console (APIs & Services → Credentials → your **Desktop app**
     client → Download JSON). Recommended.
  2. GOOGLE_DRIVE_CLIENT_ID + GOOGLE_DRIVE_CLIENT_SECRET already in .env (treated
     as an installed/desktop client).

Scope defaults to the NON-sensitive drive.file (access only to files this app
creates — all these scripts need), which shows no "unverified app" warning.

Usage:
    uv run .claude/skills/google-drive/scripts/drive_auth.py
    uv run .claude/skills/google-drive/scripts/drive_auth.py --credentials ~/Downloads/client.json

Options:
    --credentials PATH  OAuth client JSON (Desktop app). Default: search for credentials.json.
    --env PATH          .env to read client creds from / write the tokens to.
    --scope S           OAuth scope (default .../auth/drive.file; use .../auth/drive for full access).
    --port N            Loopback port (default 0 = ephemeral; Desktop clients need no registration).
    --print             Also print the refresh token to stdout (default: masked only).
    --no-browser        Print the URL instead of opening a browser (console flow).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests
from google_auth_oauthlib.flow import InstalledAppFlow

import drive_common as dc

DEFAULT_SCOPE = "https://www.googleapis.com/auth/drive.file"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def find_env_path(explicit: Path | None) -> Path:
    if explicit:
        return explicit
    d = Path.cwd()
    for parent in [d, *d.parents]:
        p = parent / ".env"
        if p.is_file():
            return p
    return d / ".env"


def find_credentials(explicit: Path | None) -> Path | None:
    if explicit:
        if not explicit.is_file():
            raise SystemExit(f"error: --credentials file not found: {explicit}")
        return explicit
    seen: list[Path] = []
    d = Path.cwd()
    seen.extend(parent / "credentials.json" for parent in [d, *d.parents])
    seen.append(Path(__file__).resolve().parent / "credentials.json")
    for c in seen:
        if c.is_file():
            return c
    return None


def upsert_env(env_path: Path, values: dict[str, str]) -> None:
    """Replace/append each KEY=value in env_path, preserving other lines."""
    lines = env_path.read_text().splitlines() if env_path.is_file() else []
    remaining = dict(values)
    out: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        key = next((k for k in remaining if stripped.startswith(f"{k}=") or stripped.startswith(f"{k} =")), None)
        if key is not None:
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(line)
    out.extend(f"{k}={v}" for k, v in remaining.items())
    env_path.write_text("\n".join(out) + "\n")


def build_flow(creds_path: Path | None, env_file: dict[str, str], scope: str) -> InstalledAppFlow:
    if creds_path is not None:
        return InstalledAppFlow.from_client_secrets_file(str(creds_path), scopes=[scope])
    client_id = dc._resolve(dc.CLIENT_ID, env_file)
    client_secret = dc._resolve(dc.CLIENT_SECRET, env_file)
    if not (client_id and client_secret):
        raise SystemExit(
            "error: no OAuth client credentials. Provide a Desktop-app credentials.json "
            f"(--credentials PATH or place one nearby), or set {dc.CLIENT_ID} + "
            f"{dc.CLIENT_SECRET} in .env. See .env.example."
        )
    config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": ["http://localhost"],
        }
    }
    return InstalledAppFlow.from_client_config(config, scopes=[scope])


def main() -> None:
    ap = argparse.ArgumentParser(description="Installed-app Google Drive OAuth -> writes creds to .env.")
    ap.add_argument("--credentials", type=Path)
    ap.add_argument("--env", type=Path)
    ap.add_argument("--scope", default=DEFAULT_SCOPE)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--print", dest="print_token", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    env_file = dc._read_env_file(args.env)
    creds_path = find_credentials(args.credentials)
    flow = build_flow(creds_path, env_file, args.scope)

    src = f"credentials.json ({creds_path})" if creds_path else ".env client id/secret"
    print(f"Using OAuth client from: {src}", file=sys.stderr)
    # access_type=offline + prompt=consent guarantee a refresh_token is returned.
    creds = flow.run_local_server(
        port=args.port,
        open_browser=not args.no_browser,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message=(
            "Open this URL to authorize:\n{url}" if args.no_browser else ""
        ),
    )

    if not creds.refresh_token:
        raise SystemExit("error: no refresh_token returned; re-run (uses prompt=consent).")

    to_write = {dc.REFRESH_TOKEN: creds.refresh_token}
    # Persist the client id/secret too so the runtime scripts can refresh.
    cfg = getattr(flow, "client_config", {}) or {}
    if cfg.get("client_id"):
        to_write[dc.CLIENT_ID] = cfg["client_id"]
    if cfg.get("client_secret"):
        to_write[dc.CLIENT_SECRET] = cfg["client_secret"]

    env_path = find_env_path(args.env)
    upsert_env(env_path, to_write)
    masked = creds.refresh_token[:6] + "…" + creds.refresh_token[-4:]
    print(f"\n✓ Wrote {', '.join(to_write)} to {env_path}", file=sys.stderr)
    print(f"  {dc.REFRESH_TOKEN} = {masked}", file=sys.stderr)
    if args.print_token:
        print(creds.refresh_token)

    # Verify end-to-end via the runtime path (refresh -> about).
    try:
        token = dc.get_access_token(args.env)
        who = requests.get(
            f"{dc.DRIVE_API}/about",
            headers={"Authorization": f"Bearer {token}"},
            params={"fields": "user(emailAddress)"},
            timeout=60,
        ).json()
        email = (who.get("user") or {}).get("emailAddress", "unknown")
        print(f"✓ Verified — Drive access as {email}", file=sys.stderr)
    except SystemExit as e:
        print(f"warning: saved token but verification failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""
drive_auth.py — one-command Google Drive OAuth via a localhost loopback.

Uses your existing GOOGLE_DRIVE_CLIENT_ID / GOOGLE_DRIVE_CLIENT_SECRET (from
.env) to run the consent flow and write a fresh GOOGLE_DRIVE_REFRESH_TOKEN back
into the same .env — so drive_upload.py / drive_download.py just work. Re-run it
any time the refresh token expires (Testing-mode tokens lapse after 7 days).

ONE-TIME console step (required): in Google Cloud Console →
APIs & Services → Credentials → your OAuth client → Authorized redirect URIs,
add EXACTLY:

    http://localhost:8765/

(Match the port if you pass --port.) Save.

Then run:

    uv run .claude/skills/google-drive/scripts/drive_auth.py

It prints (and tries to open) a Google URL. Sign in as the Drive account, click
Allow, and the token is captured, exchanged, verified, and saved automatically.

Options:
    --port N     Loopback port; must match the registered redirect URI (default 8765)
    --env PATH   Explicit .env to read creds from and write the refresh token to
    --scope S    OAuth scope (default .../auth/drive.file — non-sensitive, no
                 verification warning; use .../auth/drive for full Drive access)
    --print      Also print the refresh token to stdout (default: masked only)
    --no-browser Don't try to open a browser; just print the URL
"""
from __future__ import annotations

import argparse
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

import drive_common as dc

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
# drive.file is NON-sensitive: it grants access only to files/folders this app
# creates — exactly what these scripts do — so Google shows no "unverified app"
# warning (unlike the broad .../auth/drive scope). Override with --scope if you
# genuinely need to read/manage files the app did not create.
DEFAULT_SCOPE = "https://www.googleapis.com/auth/drive.file"


def find_env_path(explicit: Path | None) -> Path:
    """The .env to write to: the explicit one, else the first found upward, else ./.env."""
    if explicit:
        return explicit
    d = Path.cwd()
    for parent in [d, *d.parents]:
        p = parent / ".env"
        if p.is_file():
            return p
    return d / ".env"


def upsert_env(env_path: Path, key: str, value: str) -> None:
    """Replace KEY=... in env_path (preserving other lines) or append it."""
    lines = env_path.read_text().splitlines() if env_path.is_file() else []
    out, replaced = [], False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    env_path.write_text("\n".join(out) + "\n")


class _Handler(BaseHTTPRequestHandler):
    code: str | None = None
    error: str | None = None

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in ("/", ""):  # ignore /favicon.ico etc.
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(parsed.query)
        _Handler.code = (qs.get("code") or [None])[0]
        _Handler.error = (qs.get("error") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        msg = "Authorization received — you can close this tab and return to the terminal." \
            if _Handler.code else f"Authorization failed: {_Handler.error}"
        self.wfile.write(f"<html><body><h3>{msg}</h3></body></html>".encode())

    def log_message(self, *args):  # silence default logging
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Loopback Google Drive OAuth -> writes GOOGLE_DRIVE_REFRESH_TOKEN.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--env", type=Path)
    ap.add_argument("--scope", default=DEFAULT_SCOPE)
    ap.add_argument("--print", dest="print_token", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    env_file = dc._read_env_file(args.env)
    client_id = dc._resolve(dc.CLIENT_ID, env_file)
    client_secret = dc._resolve(dc.CLIENT_SECRET, env_file)
    if not (client_id and client_secret):
        raise SystemExit(
            f"error: {dc.CLIENT_ID} and {dc.CLIENT_SECRET} must be set in .env first "
            "(see .env.example)."
        )

    redirect_uri = f"http://localhost:{args.port}/"
    auth_url = f"{AUTH_ENDPOINT}?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": args.scope,
        "access_type": "offline",   # request a refresh token
        "prompt": "consent",        # force refresh token even if previously granted
    })

    try:
        server = HTTPServer(("localhost", args.port), _Handler)
    except OSError as e:
        raise SystemExit(f"error: cannot bind localhost:{args.port} ({e}). Try --port <free port> "
                         "and register that redirect URI.")

    print(f"Redirect URI (must be registered on the OAuth client): {redirect_uri}", file=sys.stderr)
    print("\nOpen this URL, sign in as the Drive account, and click Allow:\n", file=sys.stderr)
    print(auth_url + "\n", file=sys.stderr)
    if not args.no_browser:
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass

    print("Waiting for the browser redirect...", file=sys.stderr)
    while _Handler.code is None and _Handler.error is None:
        server.handle_request()
    if _Handler.error:
        raise SystemExit(f"error: authorization denied/failed: {_Handler.error}")

    # Exchange the authorization code for tokens.
    resp = requests.post(
        dc.TOKEN_ENDPOINT,
        data={
            "code": _Handler.code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=60,
    )
    if resp.status_code >= 300:
        raise SystemExit(f"error: token exchange failed: {resp.status_code} {resp.text[:300]}")
    payload = resp.json()
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise SystemExit(
            "error: Google did not return a refresh_token. Re-run (this uses prompt=consent, "
            "which should force one); ensure access_type=offline and that you approved the scope."
        )

    env_path = find_env_path(args.env)
    upsert_env(env_path, dc.REFRESH_TOKEN, refresh_token)
    masked = refresh_token[:6] + "…" + refresh_token[-4:]
    print(f"\n✓ Wrote {dc.REFRESH_TOKEN} to {env_path} ({masked})", file=sys.stderr)
    if args.print_token:
        print(refresh_token)

    # Verify end-to-end: refresh -> about.
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

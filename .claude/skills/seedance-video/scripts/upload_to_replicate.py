#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""
upload_to_replicate.py — upload local images to Replicate's Files API and return
served HTTP URLs, so full-resolution references can be passed to a prediction
WITHOUT inlining base64 into the agent context.

This is the preferred path for reference_images / image inputs whenever a
REPLICATE_API_TOKEN is available: only a short https URL travels in the
prediction input, so there is no size penalty and no context-token cost.

Token resolution order:
  1. $REPLICATE_API_TOKEN in the environment
  2. a REPLICATE_API_TOKEN=... line in a .env file (searched from the current
     directory upward, or pass --env PATH)

Usage:
    # One image -> served URL on stdout
    uv run .claude/skills/seedance-video/scripts/upload_to_replicate.py img.webp

    # Several -> JSON map {path: url}, ready to drop into reference_images
    uv run .claude/skills/seedance-video/scripts/upload_to_replicate.py a.webp b.webp --json > refs.json

Pass the returned https URL(s) directly as `reference_images` or `image`.
Uploaded files expire after ~24h by default — upload right before generating.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

FILES_ENDPOINT = "https://api.replicate.com/v1/files"


def load_token(env_path: Path | None) -> str:
    tok = os.environ.get("REPLICATE_API_TOKEN")
    if tok:
        return tok.strip()
    candidates = [env_path] if env_path else []
    if not env_path:
        # search cwd upward for a .env
        d = Path.cwd()
        for parent in [d, *d.parents]:
            candidates.append(parent / ".env")
    for c in candidates:
        if c and c.is_file():
            for line in c.read_text().splitlines():
                line = line.strip()
                if line.startswith("REPLICATE_API_TOKEN") and "=" in line:
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    raise SystemExit(
        "error: no REPLICATE_API_TOKEN found. Set it in the environment or add it "
        "to a .env file (copy .env.example). Without a token, use img2datauri.py "
        "with small --max-bytes instead."
    )


def upload(path: Path, token: str) -> str:
    with path.open("rb") as fh:
        resp = requests.post(
            FILES_ENDPOINT,
            headers={"Authorization": f"Bearer {token}"},
            files={"content": (path.name, fh)},
            timeout=120,
        )
    if resp.status_code >= 300:
        raise SystemExit(f"error: upload failed for {path.name}: {resp.status_code} {resp.text[:200]}")
    data = resp.json()
    url = (data.get("urls") or {}).get("get")
    if not url:
        raise SystemExit(f"error: no served URL in response for {path.name}: {json.dumps(data)[:200]}")
    return url


def main() -> None:
    ap = argparse.ArgumentParser(description="Upload images to Replicate Files API -> served URLs.")
    ap.add_argument("images", nargs="+", type=Path, help="Image file(s) to upload")
    ap.add_argument("--json", action="store_true", help="Emit JSON map {path: url}")
    ap.add_argument("--env", type=Path, help="Explicit path to a .env file holding REPLICATE_API_TOKEN")
    ap.add_argument("--quiet", action="store_true", help="Suppress the per-file report on stderr")
    args = ap.parse_args()

    token = load_token(args.env)
    result: dict[str, str] = {}
    for path in args.images:
        if not path.is_file():
            raise SystemExit(f"error: not a file: {path}")
        url = upload(path, token)
        result[str(path)] = url
        if not args.quiet:
            print(f"{path.name}: {path.stat().st_size:,}B -> {url}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for url in result.values():
            print(url)


if __name__ == "__main__":
    main()

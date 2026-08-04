#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""
drive_upload.py — upload local file(s) into a Google Drive folder and print the
resulting Drive links, WITHOUT routing the bytes through the agent context.

This is the storage path for the seedance-video / fred skills: reference images
and generated videos live in Google Drive rather than in git. Uploading is done
here (disk -> Drive directly) instead of via the Drive MCP, because the MCP
would require base64-inlining the whole file into the agent context (impractical
for full-res images and multi-MB videos).

The destination is a slash-separated folder path under the configured root
folder (default `xharness`) in your My Drive; missing folders are created. A
file with the same name in the target folder is updated in place, not
duplicated.

Auth comes from `.env` (see .env.example / drive_common.py): either
GOOGLE_DRIVE_ACCESS_TOKEN, or GOOGLE_DRIVE_CLIENT_ID + _CLIENT_SECRET +
_REFRESH_TOKEN.

Usage:
    S=.claude/skills/seedance-video/scripts/drive_upload.py

    # One file -> the Drive folder xharness/fred/output
    uv run $S --folder fred/output output/fred/clip.mp4

    # Many files (e.g. Fred's numbered reference set) -> xharness/fred/reference
    uv run $S --folder fred/reference /tmp/fred-refs/*.webp

    # JSON map {local_path: {id, name, webViewLink}} for scripting
    uv run $S --folder fred/images ref1.webp ref2.webp --json

Options:
    --folder PATH   Destination folder path under the root (required), e.g. "fred/images"
    --json          Emit a JSON object mapping local path -> uploaded file info
    --env PATH      Explicit path to a .env file holding the credential
    --quiet         Suppress the per-file report on stderr
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import drive_common as dc


def main() -> None:
    ap = argparse.ArgumentParser(description="Upload local files to a Google Drive folder.")
    ap.add_argument("files", nargs="+", type=Path, help="Local file(s) to upload")
    ap.add_argument("--folder", required=True,
                    help="Destination folder path under the root, e.g. 'fred/images'")
    ap.add_argument("--json", action="store_true", help="Emit JSON map {path: file_info}")
    ap.add_argument("--env", type=Path, help="Explicit path to a .env file")
    ap.add_argument("--quiet", action="store_true", help="Suppress per-file report on stderr")
    args = ap.parse_args()

    for p in args.files:
        if not p.is_file():
            raise SystemExit(f"error: not a file: {p}")

    token = dc.get_access_token(args.env)
    root = dc.get_root_name(args.env)
    folder_id = dc.resolve_folder_path(token, args.folder, create=True, root=root)

    result: dict[str, dict] = {}
    for path in args.files:
        info = dc.upload_file(token, path, folder_id)
        result[str(path)] = {
            "id": info.get("id"),
            "name": info.get("name"),
            "webViewLink": info.get("webViewLink"),
        }
        if not args.quiet:
            size = path.stat().st_size
            print(f"{path.name}: {size:,}B -> {root}/{args.folder}/  "
                  f"[{info.get('id')}] {info.get('webViewLink', '')}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for info in result.values():
            print(info.get("webViewLink") or info.get("id"))


if __name__ == "__main__":
    main()

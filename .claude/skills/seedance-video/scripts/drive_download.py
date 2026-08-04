#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""
drive_download.py — fetch file(s) from a Google Drive folder to local disk,
WITHOUT routing the bytes through the agent context.

This is the read side of Drive-backed storage for the seedance-video / fred
skills. Reference images live in Drive; at generation time this script pulls the
chosen references to a local temp dir, from where `upload_to_replicate.py` turns
them into HTTP URLs for the Seedance prediction. (Downloading via the Drive MCP
would base64-inline each image into the agent context — the very cost we avoid.)

Auth comes from `.env` (see .env.example / drive_common.py).

Usage:
    S=.claude/skills/seedance-video/scripts/drive_download.py

    # List what's in xharness/fred/images (names + ids + sizes)
    uv run $S --folder fred/images --list

    # Download two named references into a temp dir
    uv run $S --folder fred/images --dest /tmp/fredrefs \
        683523122_18079820546271388_4037734638954238058_n.webp \
        724019867_18086722952271388_6684886234545379331_n.webp

    # Download EVERYTHING in the folder
    uv run $S --folder fred/images --dest /tmp/fredrefs --all

    # JSON map {name: local_path} for scripting the ref pipeline
    uv run $S --folder fred/images --dest /tmp/fredrefs --all --json

Options:
    --folder PATH   Source folder path under the root, e.g. "fred/images" (required)
    --dest DIR      Local directory to download into (default: current dir)
    --all           Download every file in the folder
    --list          Print the folder contents and exit (no download)
    --json          Emit a JSON object mapping downloaded name -> local path
    --env PATH      Explicit path to a .env file holding the credential
    --quiet         Suppress the per-file report on stderr
    names...        Specific file names to download (unless --all/--list)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import drive_common as dc


def main() -> None:
    ap = argparse.ArgumentParser(description="Download files from a Google Drive folder.")
    ap.add_argument("names", nargs="*", help="Specific file names to download")
    ap.add_argument("--folder", required=True,
                    help="Source folder path under the root, e.g. 'fred/images'")
    ap.add_argument("--dest", type=Path, default=Path("."), help="Local download directory")
    ap.add_argument("--all", action="store_true", help="Download every file in the folder")
    ap.add_argument("--list", action="store_true", help="List folder contents and exit")
    ap.add_argument("--json", action="store_true", help="Emit JSON map {name: local_path}")
    ap.add_argument("--env", type=Path, help="Explicit path to a .env file")
    ap.add_argument("--quiet", action="store_true", help="Suppress per-file report on stderr")
    args = ap.parse_args()

    token = dc.get_access_token(args.env)
    root = dc.get_root_name(args.env)
    folder_id = dc.resolve_folder_path(token, args.folder, create=False, root=root)
    entries = dc.list_folder(token, folder_id, files_only=True)
    by_name = {e["name"]: e for e in entries}

    if args.list:
        for e in entries:
            size = e.get("size")
            size_s = f"{int(size):,}B" if size is not None else "-"
            print(f"{e['name']}\t{size_s}\t{e['id']}")
        if not entries and not args.quiet:
            print(f"(folder {root}/{args.folder} is empty)", file=sys.stderr)
        return

    if args.all:
        wanted = list(by_name.keys())
    else:
        wanted = args.names
        if not wanted:
            raise SystemExit("error: give file names to download, or --all, or --list")

    missing = [n for n in wanted if n not in by_name]
    if missing:
        raise SystemExit(
            f"error: not found in {root}/{args.folder}: {', '.join(missing)}\n"
            "Run with --list to see available names."
        )

    args.dest.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}
    for name in wanted:
        entry = by_name[name]
        dest = args.dest / name
        dc.download_file(token, entry["id"], dest)
        result[name] = str(dest)
        if not args.quiet:
            print(f"{name} -> {dest}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for path in result.values():
            print(path)


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.13"
# dependencies = ["boto3"]
# ///
"""character.py — manage on-model characters stored in the xharness-assets S3 bucket.

A character is DATA, not a skill: each one is an S3 record under `media/<name>/`
(see the `s3` skill), mirroring the existing layout:

    media/<name>/profile.md      the character bible (SOURCE OF TRUTH)
    media/<name>/reference/      curated set used on every generation
                                 (named <name>_1.<ext> … <name>_N.<ext>)
    media/<name>/originals/      optional archive to re-curate from
    media/<name>/output/         rendered videos (written by studio-video)

This tool is the management + load layer over that record. It reuses the `s3`
skill's shared helpers (`s3_common.py`: the AWS-login-bridged boto3 client, the
`media/` key mapping, natural sort), so there is one storage layer and one auth
path — nothing is base64-inlined into the agent context. Requires an AWS login
(`aws login`; see the `s3` skill).

Subcommands:
  list                         List every character (top-level folders under media/).
  show   <name>                Print the character's profile.md to stdout.
  create <name> [--from-profile FILE]
                               Create the record: upload a profile.md (the blank
                               templates/profile.md if --from-profile is omitted).
  set-profile <name> FILE      Replace the character's profile.md.
  add-refs <name> FILE...      Add reference image(s), numbered <name>_<n>.<ext>
                               continuing after the current highest index
                               (--start N / --replace to reset from 1).
  refs   <name> [--dest DIR | --presign]
                               Generation-time load of the reference set, in
                               <name>_1..N order. Default downloads to a temp dir
                               and prints a name->path JSON map; --presign instead
                               prints ordered presigned HTTPS URLs (feed straight
                               into reference_images; <name>_1 -> [Image1], …).

Examples:
  uv run .../character.py create nova --from-profile /tmp/nova.md
  uv run .../character.py add-refs nova /tmp/nova/*.webp
  uv run .../character.py refs nova --presign --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

# Reuse the s3 skill's shared helpers (one storage layer, one auth bridge).
_S3_SCRIPTS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "s3", "scripts"
)
sys.path.insert(0, os.path.abspath(_S3_SCRIPTS))
try:
    import s3_common as s3c  # noqa: E402
except ImportError:  # pragma: no cover
    print(
        "error: cannot import the s3 skill's s3_common.py — the `s3` skill must be "
        f"present at {os.path.abspath(_S3_SCRIPTS)}.",
        file=sys.stderr,
    )
    sys.exit(1)

TEMPLATE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "templates", "profile.md"
)
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
RESERVED = {"misc"}  # non-character folders under media/


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def check_name(name: str) -> None:
    if not NAME_RE.match(name) or name in RESERVED:
        die(f"invalid character name {name!r}; use lowercase [a-z0-9_-], not {sorted(RESERVED)}.")


def top_level_folders(s3) -> list[str]:
    """Immediate sub-'folders' under media/ (via a delimiter list)."""
    out: list[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=s3c.BUCKET, Prefix=s3c.MEDIA_PREFIX, Delimiter="/"):
        for cp in page.get("CommonPrefixes", []) or []:
            name = cp["Prefix"][len(s3c.MEDIA_PREFIX):].rstrip("/")
            if name:
                out.append(name)
    return sorted(out, key=s3c.natural_key)


def ref_max_index(s3, name: str) -> int:
    """Highest N among existing <name>_<N>.* objects under media/<name>/reference/."""
    pat = re.compile(rf"^{re.escape(name)}_(\d+)\.")
    hi = 0
    for key in s3c.list_prefix(s3, f"{name}/reference"):
        m = pat.match(os.path.basename(key))
        if m:
            hi = max(hi, int(m.group(1)))
    return hi


def put_file(s3, local: str, rel_key: str, content_type: str | None = None) -> str:
    import mimetypes

    ct = content_type or mimetypes.guess_type(local)[0] or "application/octet-stream"
    key = s3c.media_key(rel_key)
    s3.upload_file(local, s3c.BUCKET, key, ExtraArgs={"ContentType": ct})
    return f"s3://{s3c.BUCKET}/{key}"


# --- subcommands ----------------------------------------------------------

def cmd_list(args, s3) -> None:
    names = [f for f in top_level_folders(s3) if f not in RESERVED]
    if args.json:
        print(json.dumps(names, indent=2))
    elif names:
        print("\n".join(names))
    else:
        print("(no characters yet — create one with `character.py create <name>`)", file=sys.stderr)


def cmd_show(args, s3) -> None:
    check_name(args.name)
    key = s3c.media_key(f"{args.name}/profile.md")
    try:
        body = s3.get_object(Bucket=s3c.BUCKET, Key=key)["Body"].read()
    except s3.exceptions.NoSuchKey:
        die(f"no profile.md for character {args.name!r} (looked at s3://{s3c.BUCKET}/{key}).")
    sys.stdout.write(body.decode("utf-8"))


def cmd_create(args, s3) -> None:
    check_name(args.name)
    src = args.from_profile or TEMPLATE
    if not os.path.isfile(src):
        die(f"profile source not found: {src}")
    uri = put_file(s3, src, f"{args.name}/profile.md", "text/markdown")
    print(f"created character {args.name!r}: {uri}", file=sys.stderr)
    if src == TEMPLATE:
        print("  (blank template — fill it in, then `set-profile` the result.)", file=sys.stderr)
    print(f"  next: add references with `character.py add-refs {args.name} <img>...`", file=sys.stderr)


def cmd_set_profile(args, s3) -> None:
    check_name(args.name)
    if not os.path.isfile(args.file):
        die(f"profile file not found: {args.file}")
    uri = put_file(s3, args.file, f"{args.name}/profile.md", "text/markdown")
    print(f"updated {uri}", file=sys.stderr)


def cmd_add_refs(args, s3) -> None:
    check_name(args.name)
    missing = [f for f in args.files if not os.path.isfile(f)]
    if missing:
        die(f"file(s) not found: {', '.join(missing)}")

    if args.replace:
        start = 1
    elif args.start is not None:
        start = args.start
    else:
        start = ref_max_index(s3, args.name) + 1

    for i, f in enumerate(args.files):
        n = start + i
        ext = os.path.splitext(f)[1].lower() or ".webp"
        put_file(s3, f, f"{args.name}/reference/{args.name}_{n}{ext}", "image/webp" if ext == ".webp" else None)
    last = start + len(args.files) - 1
    print(
        f"added {len(args.files)} reference image(s) to media/{args.name}/reference/ "
        f"as {args.name}_{start}..{args.name}_{last} (slots [Image{start}]..[Image{last}])",
        file=sys.stderr,
    )


def cmd_refs(args, s3) -> None:
    check_name(args.name)
    keys = s3c.list_prefix(s3, f"{args.name}/reference")  # natural-sorted
    if not keys:
        die(f"no reference images for character {args.name!r}. Add some with `add-refs`.")

    if args.presign:
        results = [
            {
                "key": k,
                "url": s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": s3c.BUCKET, "Key": k},
                    ExpiresIn=args.expires,
                ),
            }
            for k in keys
        ]
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(r["url"])
        print(
            f"presigned {len(keys)} reference image(s) for {args.name} "
            f"({args.expires}s). Pass the urls as reference_images; cite as [Image1]…",
            file=sys.stderr,
        )
        return

    dest = args.dest or tempfile.mkdtemp(prefix=f"{args.name}-refs-")
    os.makedirs(dest, exist_ok=True)
    out: dict[str, str] = {}
    for k in keys:
        name = os.path.basename(k)
        local = os.path.join(dest, name)
        s3.download_file(s3c.BUCKET, k, local)
        out[name] = os.path.abspath(local)
    print(json.dumps(out, indent=2))
    print(
        f"downloaded {len(out)} reference image(s) to {dest}. For Replicate prefer "
        "`refs <name> --presign` (full-res, zero context cost).",
        file=sys.stderr,
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Manage on-model characters stored in S3 (media/<name>/).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list", help="List every character.")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show", help="Print a character's profile.md.")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("create", help="Create a character record (uploads a profile.md).")
    sp.add_argument("name")
    sp.add_argument("--from-profile", help="Local profile.md to seed with (default: blank template).")
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("set-profile", help="Replace a character's profile.md.")
    sp.add_argument("name")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_set_profile)

    sp = sub.add_parser("add-refs", help="Add reference image(s), numbered <name>_<n>.")
    sp.add_argument("name")
    sp.add_argument("files", nargs="+")
    sp.add_argument("--start", type=int, help="Start numbering at N (default: after current highest).")
    sp.add_argument("--replace", action="store_true", help="Number from 1 (overwrites the set in place).")
    sp.set_defaults(func=cmd_add_refs)

    sp = sub.add_parser("refs", help="Load the reference set (download, or --presign for URLs).")
    sp.add_argument("name")
    sp.add_argument("--dest", help="Local dir for a download (default: a fresh temp dir).")
    sp.add_argument("--presign", action="store_true", help="Print ordered presigned HTTPS URLs instead of downloading.")
    sp.add_argument("--expires", type=int, default=3600, help="Presign expiry seconds (default 3600).")
    sp.add_argument("--json", action="store_true", help="JSON output.")
    sp.set_defaults(func=cmd_refs)

    args = p.parse_args()
    s3 = s3c.client()
    args.func(args, s3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

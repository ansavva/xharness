#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10.0"]
# ///
"""
img2datauri.py — make any local image usable as a Replicate reference input.

Replicate's API only accepts files as HTTP(S) URLs or **data URLs**, and a data
URL must be small (the practical cap is ~256 KB). Most of the images in
`fred_images/` are larger than that. This tool shrinks an image (downscale +
recompress) until its **data URL** fits under the budget, then emits the data
URL — so any local image can be passed straight into a Seedance 2.0 prediction
as `reference_images` / `image` without hosting it anywhere.

The budget is measured on the final data-URL STRING (the exact bytes sent to the
API), so a successful result is guaranteed to fit.

Usage (via uv — no venv or manual install needed):

    S=.claude/skills/seedance-video/scripts/img2datauri.py

    # Print one data URL to stdout
    uv run $S .claude/skills/fred/images/some.webp

    # Write the data URL to a .txt sidecar instead of stdout
    uv run $S .claude/skills/fred/images/some.webp --out some.datauri.txt

    # Several images -> JSON map {path: data_url}, ready to paste as reference_images
    uv run $S .claude/skills/fred/images/*.webp --json > refs.json

    # Also drop compressed image files you can commit / host later
    uv run $S .claude/skills/fred/images/*.webp --save-dir output/compressed

    NOTE: prefer upload_to_replicate.py (full-res HTTP URLs) when a
    REPLICATE_API_TOKEN is available; use this only for the small-data-URL fallback.

Options:
    --max-bytes N   Budget for the data-URL string in bytes (default 262144 = 256 KiB)
    --format FMT    Output codec: jpeg (default) | webp | png
    --json          Emit a JSON object mapping input path -> data URL
    --out FILE      Write the (single) data URL to FILE instead of stdout
    --save-dir DIR  Also save the compressed image file(s) into DIR
    --quiet         Suppress the human-readable size report on stderr
"""
from __future__ import annotations

import argparse
import base64
import io
import sys
from pathlib import Path

from PIL import Image

MIME = {"jpeg": "image/jpeg", "webp": "image/webp", "png": "image/png"}


def encode(img: Image.Image, fmt: str, quality: int) -> bytes:
    buf = io.BytesIO()
    if fmt == "png":
        img.save(buf, format="PNG", optimize=True)
    else:
        # JPEG has no alpha; flatten onto white if needed.
        out = img
        if fmt == "jpeg" and img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            rgba = img.convert("RGBA")
            bg.paste(rgba, mask=rgba.split()[-1])
            out = bg
        elif img.mode not in ("RGB", "L"):
            out = img.convert("RGB")
        save_fmt = "JPEG" if fmt == "jpeg" else "WEBP"
        out.save(buf, format=save_fmt, quality=quality, method=6 if fmt == "webp" else None)
    return buf.getvalue()


def datauri_len(raw: bytes, mime: str) -> int:
    # len of "data:<mime>;base64," + base64 payload, without building the string.
    b64_len = (len(raw) + 2) // 3 * 4
    return len(f"data:{mime};base64,") + b64_len


def fit(path: Path, max_bytes: int, fmt: str) -> tuple[bytes, tuple[int, int]]:
    """Return (encoded_bytes, size) whose data URL is <= max_bytes."""
    mime = MIME[fmt]
    img = Image.open(path)
    img.load()
    width, height = img.size

    # Search: try decreasing quality first, then downscale, repeat.
    scale = 1.0
    for _ in range(24):  # generous cap; converges well before this
        w = max(1, int(width * scale))
        h = max(1, int(height * scale))
        resized = img if scale == 1.0 else img.resize((w, h), Image.LANCZOS)
        # PNG has no quality knob; go straight to scaling.
        qualities = [95, 85, 75, 65, 55, 45, 35, 25] if fmt != "png" else [None]
        best = None
        for q in qualities:
            raw = encode(resized, fmt, q or 0)
            if datauri_len(raw, mime) <= max_bytes:
                best = raw
                break
            best = raw  # remember smallest attempt at this scale
        if best is not None and datauri_len(best, mime) <= max_bytes:
            return best, (w, h)
        scale *= 0.85  # shrink ~15% and try again

    raise SystemExit(
        f"error: could not fit {path.name} under {max_bytes} bytes as {fmt}; "
        f"try a smaller --max-bytes target or a different --format"
    )


def to_datauri(raw: bytes, fmt: str) -> str:
    return f"data:{MIME[fmt]};base64," + base64.b64encode(raw).decode("ascii")


def main() -> None:
    ap = argparse.ArgumentParser(description="Shrink local images into Replicate-ready data URLs.")
    ap.add_argument("images", nargs="+", type=Path, help="Image file(s) to convert")
    ap.add_argument("--max-bytes", type=int, default=256 * 1024, help="Data-URL byte budget (default 262144)")
    ap.add_argument("--format", choices=list(MIME), default="jpeg", help="Output codec (default jpeg)")
    ap.add_argument("--json", action="store_true", help="Emit JSON map {path: data_url}")
    ap.add_argument("--out", type=Path, help="Write the single data URL to this file")
    ap.add_argument("--save-dir", type=Path, help="Also save compressed image file(s) here")
    ap.add_argument("--quiet", action="store_true", help="Suppress size report on stderr")
    args = ap.parse_args()

    if args.out and len(args.images) > 1:
        raise SystemExit("error: --out works with a single image; use --json for multiple")
    if args.save_dir:
        args.save_dir.mkdir(parents=True, exist_ok=True)

    ext = {"jpeg": "jpg", "webp": "webp", "png": "png"}[args.format]
    result: dict[str, str] = {}
    for path in args.images:
        if not path.is_file():
            raise SystemExit(f"error: not a file: {path}")
        raw, (w, h) = fit(path, args.max_bytes, args.format)
        uri = to_datauri(raw, args.format)
        result[str(path)] = uri
        if args.save_dir:
            dest = args.save_dir / f"{path.stem}.{ext}"
            dest.write_bytes(raw)
        if not args.quiet:
            print(
                f"{path.name}: {path.stat().st_size:,}B -> {len(raw):,}B "
                f"({w}x{h}, data-url {len(uri):,}B)",
                file=sys.stderr,
            )

    if args.json:
        import json

        print(json.dumps(result, indent=2))
    elif args.out:
        args.out.write_text(next(iter(result.values())))
        if not args.quiet:
            print(f"wrote {args.out}", file=sys.stderr)
    else:
        for uri in result.values():
            print(uri)


if __name__ == "__main__":
    main()

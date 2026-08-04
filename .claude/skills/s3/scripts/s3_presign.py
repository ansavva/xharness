# /// script
# requires-python = ">=3.13"
# dependencies = ["boto3"]
# ///
"""Generate temporary HTTPS URLs for objects in the media tree.

This is how S3-hosted images/videos reach Replicate/Seedance: a short-lived
presigned GET URL that Replicate fetches during the job. The bucket stays
private; no credentials are exposed.

  # every reference image, in fred_1..fred_N order -> [Image1]..[ImageN]
  uv run .../s3_presign.py --folder fred/reference --json

  # specific objects under a folder
  uv run .../s3_presign.py --folder fred/reference fred_1.webp fred_2.webp

  # one exact key relative to media/
  uv run .../s3_presign.py --key fred/output/clip.mp4
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3_common as s3c  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--folder", help="Path under media/ (e.g. fred/reference).")
    ap.add_argument("--key", help="An exact key relative to media/ (e.g. fred/output/clip.mp4).")
    ap.add_argument("names", nargs="*", help="With --folder: specific basenames (default: all in the folder).")
    ap.add_argument("--expires", type=int, default=3600, help="Expiry in seconds (default 3600).")
    ap.add_argument("--json", action="store_true", help="Emit JSON [{key,url}] instead of one URL per line.")
    args = ap.parse_args()

    if not args.folder and not args.key:
        s3c.die("pass --folder <path> or --key <path>.")

    s3 = s3c.client()

    if args.key:
        keys = [s3c.media_key(args.key)]
    else:
        folder = args.folder.strip("/")
        all_keys = s3c.list_prefix(s3, folder)
        if args.names:
            by_name = {os.path.basename(k): k for k in all_keys}
            missing = [n for n in args.names if n not in by_name]
            if missing:
                s3c.die(f"not found under media/{folder}/: {', '.join(missing)}")
            keys = [by_name[n] for n in args.names]
        else:
            keys = all_keys
        if not keys:
            s3c.die(f"no objects under media/{folder}/")

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


if __name__ == "__main__":
    main()

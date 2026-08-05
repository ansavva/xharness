# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Submit a Seedance 2.0 prediction to Replicate — minting FRESH presigned
reference URLs in code at submit time, so no long S3 URL is ever hand-copied.

This is the reliable path for character videos. Hand-pasting presigned URLs into
a tool call is error-prone (one wrong character → a 400/expired fetch and a dead
render) and the URLs expire; this script regenerates them from the `s3` skill
right before it POSTs, then submits directly to the Replicate HTTP API using
`REPLICATE_API_TOKEN` (from the repo `.env`).

  # input.json = the built Replicate `input` object WITHOUT reference_images
  # (e.g. `build_prompt.py prompt.json --emit input` → the .input object)
  uv run submit_prediction.py --input-file input.json --character <name>
  uv run submit_prediction.py --input-file input.json --character <name> --slots 1,2,3,6 --poll

Prints the created prediction id (and, with --poll, waits for a terminal status
and prints the output video URL). Reference slots map to [Image1..N] in prompt
order. Omit --slots to use the whole reference set.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CHARACTER_PY = os.path.abspath(os.path.join(HERE, "..", "..", "studio-character", "scripts", "character.py"))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
API = "https://api.replicate.com/v1/models/bytedance/seedance-2.0/predictions"


def die(msg: str) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_token() -> str:
    tok = os.environ.get("REPLICATE_API_TOKEN")
    if tok:
        return tok.strip()
    env = os.path.join(REPO_ROOT, ".env")
    if os.path.isfile(env):
        for line in open(env):
            line = line.strip()
            if line.startswith("REPLICATE_API_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    die("REPLICATE_API_TOKEN not set (env or repo .env).")


def fresh_presigned_refs(character: str, slots: list[int] | None, expires: int) -> list[str]:
    """Mint fresh ordered presigned URLs via the character skill (which uses s3)."""
    out = subprocess.run(
        ["uv", "run", CHARACTER_PY, "refs", character, "--presign", "--json", "--expires", str(expires)],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        die(f"presign failed:\n{out.stderr.strip()}")
    entries = json.loads(out.stdout)  # [{key, url}, ...] natural-sorted, images only
    if slots:
        by_n = {}
        for e in entries:
            base = os.path.basename(e["key"])
            stem = os.path.splitext(base)[0]  # e.g. <name>_3
            n = int(stem.rsplit("_", 1)[-1])
            by_n[n] = e["url"]
        missing = [s for s in slots if s not in by_n]
        if missing:
            die(f"slots not found in reference set: {missing}")
        return [by_n[s] for s in slots]
    return [e["url"] for e in entries]


def api(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        die(f"{method} {url} -> {e.code}: {e.read().decode()[:500]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-file", required=True, help="JSON file: the Replicate `input` object WITHOUT reference_images.")
    ap.add_argument("--character", required=True, help="Character whose reference set to presign (e.g. <name>).")
    ap.add_argument("--slots", help="Comma-separated reference numbers to use, e.g. 1,2,3,6 (default: all).")
    ap.add_argument("--expires", type=int, default=3600, help="Presign expiry seconds (default 3600).")
    ap.add_argument("--poll", action="store_true", help="Wait for a terminal status and print the output URL.")
    ap.add_argument("--interval", type=int, default=15, help="Poll interval seconds (default 15).")
    args = ap.parse_args()

    token = load_token()
    inp = json.load(open(args.input_file))
    if "reference_images" in inp:
        # Never trust stale refs baked into the file — always mint fresh below.
        del inp["reference_images"]
    slots = [int(s) for s in args.slots.split(",")] if args.slots else None

    inp["reference_images"] = fresh_presigned_refs(args.character, slots, args.expires)
    print(f"minted {len(inp['reference_images'])} fresh presigned reference URL(s)", file=sys.stderr)

    created = api("POST", API, token, {"input": inp})
    pid = created.get("id")
    print(json.dumps({"id": pid, "status": created.get("status")}, indent=2))
    if not args.poll or not pid:
        return

    get_url = f"https://api.replicate.com/v1/predictions/{pid}"
    while True:
        time.sleep(args.interval)
        cur = api("GET", get_url, token)
        st = cur.get("status")
        print(f"  {st}", file=sys.stderr)
        if st in ("succeeded", "failed", "canceled"):
            print(json.dumps({"id": pid, "status": st, "output": cur.get("output"), "error": cur.get("error")}, indent=2))
            return


if __name__ == "__main__":
    main()

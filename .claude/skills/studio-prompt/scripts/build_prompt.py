#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Assemble + validate a Seedance 2.0 "JSON prompt" and split it into the
serialized prompt string and the Replicate API input params.

Seedance's `prompt` field is a plain TEXT string. "JSON prompting" means
serializing a structured object into that string; the model reads structured
text consistently. This tool:

  1. takes a structured object (creative blocks + a `technical` block),
  2. validates the well-known Seedance prompting rules (one camera move, no
     bare "fast", no camera verbs in the action, no vague adjectives, …),
  3. ROUTES the technical fields to the real Replicate input params
     (aspect_ratio / duration / resolution / seed / generate_audio) instead of
     leaving them in the prompt text, and
  4. emits {prompt, input, warnings, errors, timeline} as JSON.

Key ordering follows ByteDance's own guidance — SUBJECT + ACTION lead, because
"the first 20-30 words carry the most weight" — not the camera-first order some
third-party guides push.

Note: Seedance/Replicate has NO negative_prompt param, so a `negative` stays
INSIDE the serialized JSON prompt (as an "avoid" key), never in `input`.

Usage:
  build_prompt.py prompt.json
  build_prompt.py - < prompt.json
  build_prompt.py --json '{"subject": "...", "action": "..."}'
  build_prompt.py prompt.json --duration 8 --aspect-ratio 9:16 --emit input

Author the object like:
  {
    "subject": "A young woman in a white linen dress",
    "action": "Slowly turns to face the sea, skirt lifting in the breeze",
    "scene": "Rocky coastline at dusk, warm golden haze",
    "camera": {"shot": "medium", "movement": "slow push-in", "lens_mm": 35, "speed": "slow"},
    "lighting": "Low golden-hour sun, soft rim light",
    "style": "Cinematic film tone, gentle contrast, 35mm grain",
    "audio": "Soft wind, distant gulls",
    "dialogue": ["It's finally quiet out here."],
    "negative": "jitter, bent limbs, temporal flicker, extra fingers",
    "technical": {"aspect_ratio": "16:9", "duration": 6, "resolution": "1080p", "generate_audio": true}
  }

For a multi-shot piece, use timeline mode by supplying `shots`:
  {
    "subject": "A detective in a long coat",
    "style": "Neo-noir, teal/amber grade",
    "shots": [
      {"t": "0s", "shot": "wide",   "camera": "static",          "description": "Stands at the end of a rain-slicked street"},
      {"t": "3s", "shot": "medium", "camera": "slow dolly in",    "description": "Camera closes in from behind"},
      {"t": "6s", "shot": "close",  "camera": "hold",             "description": "Rain beads on his collar; he exhales"}
    ],
    "technical": {"duration": 8, "aspect_ratio": "21:9"}
  }
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# --- Replicate input enums (from bytedance/seedance-2.0) --------------------
RESOLUTIONS = {"480p", "720p", "1080p", "4k"}
ASPECT_RATIOS = {"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "9:21", "adaptive"}

# Fields that map to REAL Replicate input params (not prompt text).
TECHNICAL_TO_INPUT = {"aspect_ratio", "duration", "resolution", "seed", "generate_audio"}
# jsonpromptstudio invents these; Seedance/Replicate has no such param. Warn + drop.
UNSUPPORTED_TECHNICAL = {"fps", "creativity", "lock_identity", "lock_style", "negative_prompt"}

# Ordered creative keys for the serialized prompt (subject/action FIRST).
PROMPT_KEY_ORDER = ["subject", "action", "scene", "camera", "lighting", "style", "audio", "dialogue", "avoid"]

# Camera-movement vocabulary — used to detect stacking and misplaced verbs.
CAMERA_MOVES = [
    "push-in", "push in", "pull-out", "pull out", "dolly", "pan", "tilt",
    "tracking", "track", "orbit", "aerial", "drone", "crane", "handheld",
    "zoom", "rack focus", "whip",
]
VAGUE_ADJECTIVES = [
    "amazing", "beautiful", "epic", "stunning", "gorgeous", "breathtaking",
    "awesome", "incredible", "majestic", "magical",
]


def _err(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)


def load_object(args: argparse.Namespace) -> dict:
    """Load the base structured object from a file, stdin, or --json."""
    raw = None
    if args.json is not None:
        raw = args.json
    elif args.source == "-":
        raw = sys.stdin.read()
    elif args.source:
        with open(args.source, encoding="utf-8") as fh:
            raw = fh.read()
    else:
        return {}
    raw = raw.strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        _err(f"input is not valid JSON: {exc}")
        sys.exit(2)
    if not isinstance(obj, dict):
        _err("top-level JSON must be an object")
        sys.exit(2)
    return obj


def apply_overrides(obj: dict, args: argparse.Namespace) -> None:
    """CLI flags override values inside the loaded object."""
    for key in ("subject", "action", "scene", "style", "lighting", "audio", "negative"):
        val = getattr(args, key)
        if val is not None:
            obj[key] = val

    cam = obj.get("camera")
    if not isinstance(cam, dict):
        cam = {} if cam is None else {"movement": str(cam)}
    if args.camera_movement is not None:
        cam["movement"] = args.camera_movement
    if args.camera_shot is not None:
        cam["shot"] = args.camera_shot
    if args.lens_mm is not None:
        cam["lens_mm"] = args.lens_mm
    if cam:
        obj["camera"] = cam

    tech = obj.get("technical")
    if not isinstance(tech, dict):
        tech = {}
    if args.aspect_ratio is not None:
        tech["aspect_ratio"] = args.aspect_ratio
    if args.duration is not None:
        tech["duration"] = args.duration
    if args.resolution is not None:
        tech["resolution"] = args.resolution
    if args.seed is not None:
        tech["seed"] = args.seed
    if args.no_audio:
        tech["generate_audio"] = False
    if tech:
        obj["technical"] = tech


def _text_fields(obj: dict) -> dict[str, str]:
    """Flatten the creative text into {field: text} for scanning."""
    out: dict[str, str] = {}
    for k in ("subject", "action", "scene", "style", "lighting", "audio", "negative"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v
    cam = obj.get("camera")
    if isinstance(cam, dict):
        for ck in ("shot", "movement", "speed"):
            v = cam.get(ck)
            if isinstance(v, str) and v.strip():
                out[f"camera.{ck}"] = v
    for i, shot in enumerate(obj.get("shots") or []):
        if isinstance(shot, dict):
            for sk in ("camera", "description"):
                v = shot.get(sk)
                if isinstance(v, str) and v.strip():
                    out[f"shots[{i}].{sk}"] = v
    return out


def validate(obj: dict) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    fields = _text_fields(obj)

    # --- one camera movement only -----------------------------------------
    cam = obj.get("camera")
    if isinstance(cam, dict):
        move = str(cam.get("movement", "") or "")
        low = move.lower()
        if move:
            # stacking detected via connectors or 2+ distinct move verbs.
            # Match on word boundaries, then drop hits that are substrings of a
            # longer hit ("track" inside "tracking") so one move isn't counted twice.
            raw = {m for m in CAMERA_MOVES if re.search(rf"(?<!\w){re.escape(m)}(?!\w)", low)}
            hits = {m for m in raw if not any(m != o and m in o for o in raw)}
            connector = bool(re.search(r"\b(and|then|\+|,|while|followed by)\b", low))
            if len(hits) >= 2 or (connector and hits):
                warnings.append(
                    f"camera.movement stacks multiple moves ({move!r}); Seedance "
                    "degrades on stacked moves — keep one shot type + one movement."
                )

    # --- bare 'fast' -------------------------------------------------------
    for field, text in fields.items():
        if re.search(r"\bfast\b", text.lower()) and field.startswith("camera"):
            warnings.append(
                f"{field} uses bare 'fast' ({text!r}); qualify the speed "
                "(e.g. 'fast whip-pan', 'quick 1s push-in') — bare 'fast' causes chaos."
            )

    # --- camera verbs leaking into subject/action -------------------------
    for field in ("subject", "action"):
        text = fields.get(field, "").lower()
        leaked = sorted({m for m in CAMERA_MOVES if re.search(rf"\b{re.escape(m)}\b", text)})
        if leaked:
            warnings.append(
                f"{field} contains camera-move words {leaked}; move camera "
                "direction into the `camera` block, keep this block to subject motion."
            )

    # --- vague adjectives --------------------------------------------------
    for field, text in fields.items():
        if field in ("audio", "negative"):
            continue
        found = sorted({a for a in VAGUE_ADJECTIVES if re.search(rf"\b{a}\b", text.lower())})
        if found:
            warnings.append(
                f"{field} uses vague adjective(s) {found}; replace with concrete, "
                "observable detail (Seedance ignores mood words like these)."
            )

    # --- technical block routing ------------------------------------------
    tech = obj.get("technical")
    if isinstance(tech, dict):
        for k in tech:
            if k in UNSUPPORTED_TECHNICAL:
                if k == "negative_prompt":
                    warnings.append(
                        "technical.negative_prompt is not a Replicate param; it was "
                        "folded into the prompt as `avoid` instead. Use the top-level "
                        "`negative` key going forward."
                    )
                else:
                    warnings.append(
                        f"technical.{k} is not a real bytedance/seedance-2.0 param; "
                        "dropped. (Some third-party guides invent it.)"
                    )
        ar = tech.get("aspect_ratio")
        if ar is not None and ar not in ASPECT_RATIOS:
            errors.append(f"aspect_ratio {ar!r} invalid; choose one of {sorted(ASPECT_RATIOS)}.")
        res = tech.get("resolution")
        if res is not None and res not in RESOLUTIONS:
            errors.append(f"resolution {res!r} invalid; choose one of {sorted(RESOLUTIONS)}.")
        dur = tech.get("duration")
        if dur is not None and not (dur == -1 or (isinstance(dur, int) and 1 <= dur <= 15)):
            errors.append(f"duration {dur!r} invalid; use an int 1-15, or -1 for intelligent duration.")

    # --- must have SOMETHING to render ------------------------------------
    if not obj.get("shots") and not obj.get("subject") and not obj.get("action"):
        errors.append("nothing to render: provide at least `subject`/`action`, or a `shots` timeline.")

    return warnings, errors


def build_prompt_object(obj: dict) -> tuple[dict, bool]:
    """Return (ordered creative object for serialization, is_timeline)."""
    timeline = bool(obj.get("shots"))
    out: dict = {}

    # `negative` -> `avoid` inside the prompt (no API param exists for it).
    neg = obj.get("negative")
    tech = obj.get("technical") if isinstance(obj.get("technical"), dict) else {}
    if not neg and isinstance(tech, dict):
        neg = tech.get("negative_prompt")

    if timeline:
        # globals first, then the ordered shot list.
        for k in ("subject", "style", "audio", "lighting"):
            v = obj.get(k)
            if v:
                out[k] = v
        clean_shots = []
        for shot in obj["shots"]:
            if isinstance(shot, dict):
                clean_shots.append({k: v for k, v in shot.items() if v not in (None, "", [])})
            else:
                clean_shots.append(shot)
        out["shots"] = clean_shots
        if neg:
            out["avoid"] = neg
        return out, timeline

    # single-shot: subject/action FIRST, then the rest in canonical order.
    src = dict(obj)
    if neg:
        src["avoid"] = neg
    for key in PROMPT_KEY_ORDER:
        v = src.get(key)
        if v in (None, "", [], {}):
            continue
        if key == "camera" and isinstance(v, dict):
            v = {ck: cv for ck, cv in v.items() if cv not in (None, "")}
            if not v:
                continue
        out[key] = v
    return out, timeline


def build_input(obj: dict, prompt_str: str) -> dict:
    """Assemble the Replicate `input` dict (creative content -> prompt str)."""
    inp: dict = {"prompt": prompt_str}
    tech = obj.get("technical")
    if isinstance(tech, dict):
        for k in TECHNICAL_TO_INPUT:
            if k in tech and tech[k] is not None:
                inp[k] = tech[k]
    return inp


def main() -> int:
    p = argparse.ArgumentParser(
        description="Build + validate a Seedance 2.0 JSON prompt and split it into "
        "a serialized prompt string and Replicate input params.",
    )
    p.add_argument("source", nargs="?", help="Path to a JSON object file, or '-' for stdin.")
    p.add_argument("--json", help="Inline JSON object (overrides source).")
    # creative overrides
    p.add_argument("--subject")
    p.add_argument("--action")
    p.add_argument("--scene")
    p.add_argument("--style")
    p.add_argument("--lighting")
    p.add_argument("--audio")
    p.add_argument("--negative")
    p.add_argument("--camera-movement")
    p.add_argument("--camera-shot")
    p.add_argument("--lens-mm", type=int)
    # technical overrides
    p.add_argument("--aspect-ratio")
    p.add_argument("--duration", type=int)
    p.add_argument("--resolution")
    p.add_argument("--seed", type=int)
    p.add_argument("--no-audio", action="store_true", help="Set generate_audio=false.")
    # output control
    p.add_argument("--emit", choices=["both", "prompt", "input"], default="both")
    p.add_argument("--compact", action="store_true", help="Single-line prompt JSON (no indent).")
    p.add_argument("--strict", action="store_true", help="Exit non-zero if any warnings.")
    args = p.parse_args()

    obj = load_object(args)
    apply_overrides(obj, args)

    warnings, errors = validate(obj)
    if errors:
        for e in errors:
            _err(e)
        return 2

    prompt_obj, timeline = build_prompt_object(obj)
    prompt_str = json.dumps(
        prompt_obj,
        ensure_ascii=False,
        indent=None if args.compact else 2,
        separators=(",", ":") if args.compact else None,
    )
    inp = build_input(obj, prompt_str)

    if args.emit == "prompt":
        payload: dict = {"prompt": prompt_str}
    elif args.emit == "input":
        payload = {"input": inp}
    else:
        payload = {"prompt": prompt_str, "input": inp}
    payload["timeline"] = timeline
    payload["warnings"] = warnings

    print(json.dumps(payload, ensure_ascii=False, indent=2))

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

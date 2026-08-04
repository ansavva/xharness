---
name: seedance-video
description: Generate videos on demand with ByteDance Seedance 2.0 via the Replicate MCP — the engine for any text-to-video / image-to-video / character-video request. Use whenever the user wants to create, generate, or render a video, clip, animation, or motion piece (with optional native audio, first/last-frame images, or reference images/videos/audio). Covers the model input schema, the create-then-poll flow, output naming, and how local images must be passed (base64 data URLs vs HTTP URLs). Character videos additionally load that character's own skill (e.g. `fred`) for on-model references.
---

# Seedance 2.0 video generation

Generate videos by creating a Replicate prediction against
**`bytedance/seedance-2.0`** (<https://replicate.com/bytedance/seedance-2.0>)
through the **Replicate MCP server**, polling it, and saving the output MP4.
There is no build step — the "work" is the MCP call, the poll, and the download.

> **Character videos:** if the request names a known character (e.g. Fred),
> FIRST load that character's skill (`fred`) — it supplies the profile and the
> reference images this engine requires. Never generate a character from a text
> prompt alone (see "Reference images are MANDATORY" below).

## The model: `bytedance/seedance-2.0`

Multimodal video generation with **native audio**, multimodal reference inputs
(images / video / audio), and intelligent duration control. Output is a single
video file URL.

### Input schema

| Field | Type | Default | Notes |
|---|---|---|---|
| `prompt` | string (**required**) | — | Max 4000 chars; keep under ~600 English words. Put **spoken dialogue in double quotes** to drive audio. |
| `image` | uri | null | First-frame image for image-to-video. **Cannot** be combined with `reference_images`. |
| `last_frame_image` | uri | null | Last-frame image. Only works when `image` is also set. Not combinable with reference images. |
| `reference_images` | uri[] (≤ 9) | `[]` | For **character consistency**, style, and scene composition. Reference them in the prompt as `[Image1]`, `[Image2]`, … **Cannot** be combined with `image`/`last_frame_image`. |
| `reference_videos` | uri[] (≤ 3, ≤ 15s total) | `[]` | Motion transfer / style / editing. Reference as `[Video1]`, … |
| `reference_audios` | uri[] (≤ 3, ≤ 15s total) | `[]` | Audio-driven generation / lip-sync. Requires ≥1 reference image or video. Reference as `[Audio1]`, … |
| `duration` | int | `5` | 1–15 seconds. Set to `-1` for intelligent duration (model picks length). |
| `resolution` | enum | `720p` | `480p` · `720p` · `1080p` · `4k` (4K = 10-bit H.265/HEVC). |
| `aspect_ratio` | enum | `16:9` | `16:9` · `4:3` · `1:1` · `3:4` · `9:16` · `21:9` · `9:21` · `adaptive`. |
| `generate_audio` | bool | `true` | Synced dialogue, SFX, and music. |
| `seed` | int | null | Set for reproducible generation. |

Key constraint: **`image`/`last_frame_image` and `reference_images` are mutually
exclusive.** Use `image` for a specific first frame; use `reference_images` when
you want a character/style carried across a freshly composed scene.

## How to generate a video

Use the Replicate MCP tool `create_models_predictions` with
`model_owner: "bytedance"`, `model_name: "seedance-2.0"`, and an `input` object.

**Do NOT set `Prefer: wait` on video jobs.** Seedance renders always take longer
than the 60s wait window, and a timed-out `wait` call retries internally —
creating **duplicate predictions that all bill** (this happened once and spent
~2 clips of compute for one result). Instead, create the prediction with no
`wait`, take the returned `prediction_id`, and poll `get_predictions` until
`status` is `succeeded`, `failed`, or `canceled`. On success, `output` is the
video URL — download it with `curl` and hand the local path back to the user.

If a create call ever errors or times out, **don't blindly re-create it** —
first `list_predictions` (filtered to `bytedance/seedance-2.0`) to see whether a
job is already `processing`/`succeeded`, and `cancel_predictions` any duplicates.

### Output location (always)

Save **every** generated video under `output/<character>/` at the repo root, with
a date-time in the filename so runs never overwrite each other. Use the format
`YYYY-MM-DD_HH-MM-SS` (local time). For a video not tied to a character, use
`output/misc/`. The `output/` directory is git-ignored. Create it if missing.

```bash
mkdir -p output/fred
curl -sL "<output_url>" -o "output/fred/$(date +%Y-%m-%d_%H-%M-%S)_<slug>.mp4"
```

Pick a short descriptive `<slug>` (e.g. `waving-9x16`), so a filename looks like
`output/fred/2026-08-03_19-42-05_waving-9x16.mp4`. Then report the saved path.

Minimal example input:

```json
{
  "prompt": "A golden retriever runs across a sunny beach, waves crashing. \"Come on, let's go!\"",
  "duration": 5,
  "resolution": "1080p",
  "aspect_ratio": "16:9"
}
```

### Reference images are MANDATORY for any character video

**Rule (non-negotiable): never generate a video of a known character without
passing that character's reference images in `reference_images`.** A text prompt
alone drifts off-model — a character's profile + images exist to be *wired into
the request*, not merely read. If you are about to call the model with only a
`prompt` for a character, STOP and add `reference_images` first.

- Seedance 2.0 accepts up to **9** `reference_images`. Reference them in the
  prompt as `[Image1]`, `[Image2]`, … Use 2–4 that match the target
  angle / wardrobe / build.
- `reference_images` **cannot** be combined with `image` / `last_frame_image`.

### How image files reach Replicate (base64 data URLs vs HTTP URLs)

Replicate accepts a file input only in one of two forms:

- **HTTP(S) URL** — best for anything **> 256 KB**, for reuse, or for many
  files. Only a short URL travels in the request; Replicate fetches the image.
- **data URL** — the image base64-encoded inline as
  `data:image/jpeg;base64,<...>`. Replicate's guidance caps data URLs at
  **≤ 256 KB**. Nothing is hosted and Replicate does not store it.

Two helper scripts live beside this skill:

```bash
# 1) Local image -> fitting data URL (downscale/recompress until it fits --max-bytes)
uv run .claude/skills/seedance-video/scripts/img2datauri.py <img> --max-bytes 12000 --out ref1.txt
uv run .claude/skills/seedance-video/scripts/img2datauri.py <img>... --json > refs.json

# 2) Local image -> HTTP URL via Replicate Files API (needs REPLICATE_API_TOKEN; see .env)
uv run .claude/skills/seedance-video/scripts/upload_to_replicate.py <img>... --json > refs.json
```

`img2datauri.py` flags: `--json`, `--out FILE`, `--max-bytes N` (default 262144),
`--format jpeg|webp|png`, `--save-dir DIR`.

### Full-res references vs the small-data-URL workaround (important)

**Seedance and Replicate do NOT require tiny references.** Sharper references
give better character consistency. With a `REPLICATE_API_TOKEN` configured in
`.env`, the base64/context limitation below is **fully overcome** — upload
full-size images and pass HTTP URLs (only short URLs enter the agent context).
Two ways to supply references:

- **PREFERRED — HTTP URLs (full resolution, zero context cost).** With a
  `REPLICATE_API_TOKEN` present (put it in `.env` at the repo root, copied from
  `.env.example`), run `upload_to_replicate.py` to POST each image to
  `https://api.replicate.com/v1/files` and get back a served URL. Only short URLs
  go into the prediction `input` — no base64 ever enters the agent context, so
  images can be full size. **Use this whenever the token is available.**
- **FALLBACK — inline data URLs, kept small.** Without a token, the only path is
  inlining the base64 data URL into the MCP tool call. That base64 lands in the
  agent context, where it tokenizes at ≈ **1 token per character** (an 80 KB data
  URL ≈ 80k tokens, paid on read + write), so a few full-size refs would blow the
  context window. Cap each data URL at ~10–15 KB via `img2datauri.py --max-bytes
  12000`. Seedance downsamples references anyway, so small refs still steer
  identity/style/wardrobe — just with weaker fine detail. This smallness is an
  agent-tooling limit, **not** a model limit.

## Available Replicate MCP tools (common)

- `get_models` / `get_models_readme` — inspect a model's schema and docs.
- `create_models_predictions` — run an official model (this one).
- `get_predictions` / `list_predictions` — poll or list runs.
- `cancel_predictions` — cancel a running job.
- `search` / `search_docs` — find models and client usage docs.

Always pass a `jq_filter` to these tools to keep responses small (e.g.
`{id, status, output, error}` when polling).

## Characters

Each character owns its own skill under `.claude/skills/<name>/`, self-contained
with a `profile.md` (the character bible) and an `images/` directory. That skill
reads the profile, picks + converts reference images, and composes the prompt so
the output stays on-model. This engine skill is character-agnostic.

- **Fred** — recurring illustrated character (the "Gays of Hudson" series).
  Skill: `.claude/skills/fred/`.

### Adding a new character

1. `.claude/skills/<name>/SKILL.md` — copy the Fred skill as a template and
   rewrite the prompt template + guardrails for the new character.
2. `.claude/skills/<name>/profile.md` — the character bible (mirror Fred's
   sections: at-a-glance, face, body, wardrobe, art style, voice, checklist).
3. `.claude/skills/<name>/images/` — drop reference images here.
4. Videos save to `output/<name>/`. No change to this engine skill is needed.

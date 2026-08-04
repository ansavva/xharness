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

### Output location (always) — save to S3

Generated videos are stored in **S3** (bucket `xharness-assets`), not in git.
Save **every** video under `media/<character>/output/`; for a video not tied to a
character use `media/misc/output/`. Give the filename a date-time so runs never
overwrite each other: `YYYY-MM-DD_HH-MM-SS_<slug>.mp4` with a short descriptive
`<slug>` (e.g. `waving-9x16`).

The flow is download-then-upload — Replicate's output URL → a local staging file
→ S3 — so the video bytes never pass through the agent context:

```bash
# 1) stage the render locally (output/ is git-ignored)
mkdir -p output/fred
NAME="$(date +%Y-%m-%d_%H-%M-%S)_<slug>.mp4"
curl -sL "<output_url>" -o "output/fred/$NAME"

# 2) upload the staged file to S3 (media/fred/output/) — s3 skill
uv run .claude/skills/s3/scripts/s3_upload.py \
  --folder fred/output "output/fred/$NAME"
```

Report the `s3://` URI that `s3_upload.py` prints (add `--presign` for a
shareable HTTPS link). The local `output/fred/` copy is just staging; S3 is the
canonical store. Uploading needs an AWS login (`aws login`; see the `s3` skill);
without one, leave the file in `output/` and tell the user it wasn't pushed to S3.

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
  prompt as `[Image1]`, `[Image2]`, …
- Each character keeps a **fixed, numbered reference set in S3** (at
  `media/<character>/reference/`), used in full on every generation so identity
  stays locked without re-picking. Presign it with `s3_presign.py --folder
  <character>/reference` to get ordered HTTPS URLs (below). The character's own
  skill (e.g. `fred`) documents its set.
- `reference_images` **cannot** be combined with `image` / `last_frame_image`.

### How image files reach Replicate (presigned S3 URLs)

Replicate accepts a file input as a URL or an inline data URL. Since references
and outputs live in **S3**, the primary path is a **presigned HTTPS URL**: the
object stays private, Replicate fetches it via a short-lived signed URL, and only
a short URL (never the bytes) enters the agent context. No `REPLICATE_API_TOKEN`
is needed for references.

```bash
# References: presign a character's fixed set, in fred_1..fred_N order, as JSON (s3 skill)
uv run .claude/skills/s3/scripts/s3_presign.py --folder fred/reference --json > refs.json
# -> [{ "key": "media/fred/reference/fred_1.webp", "url": "https://..." }, ...]
# Pass the .url values as reference_images; fred_1 -> [Image1], fred_2 -> [Image2], ...

# After rendering: upload the finished MP4 to S3 (s3 skill)
uv run .claude/skills/s3/scripts/s3_upload.py --folder fred/output output/fred/<name>.mp4
```

Fallbacks for ad-hoc **local** images not in S3 (the Replicate-side helpers live
beside this skill):

```bash
# Local image -> HTTP URL via Replicate Files API (needs REPLICATE_API_TOKEN; see .env)
uv run .claude/skills/seedance-video/scripts/upload_to_replicate.py <img>... --json > refs.json

# No token? Local image -> small inline data URL (downscale/recompress to fit --max-bytes)
uv run .claude/skills/seedance-video/scripts/img2datauri.py <img>... --max-bytes 12000 --json > refs.json
```

`img2datauri.py` flags: `--json`, `--out FILE`, `--max-bytes N` (default 262144),
`--format jpeg|webp|png`, `--save-dir DIR`. Presigned S3 URLs default to a 1 h
expiry (`--expires` to change) — plenty for a render job. See the **`s3`** skill
for details and `aws login` setup.

### Full-res references, zero context cost

**Seedance and Replicate do NOT require tiny references** — sharper references
give better character consistency, and presigned S3 URLs carry full-resolution
images at zero context cost (only the short URL enters the agent context). Order
of preference:

- **PREFERRED — presigned S3 URLs (full resolution).** References already live in
  S3, so `s3_presign.py` hands Replicate full-size images via signed URLs. No
  token, no base64. Use this for any character reference set.
- **Local image, have a token — Replicate Files API.** For an ad-hoc local image
  not in S3, `upload_to_replicate.py` (needs `REPLICATE_API_TOKEN`) POSTs it and
  returns a served URL — again full size, only a short URL in context.
- **Local image, no token — inline data URL, kept small.** Last resort: inline a
  base64 data URL into the MCP call. That base64 lands in the agent context at ≈
  **1 token per character** (an 80 KB data URL ≈ 80k tokens), so cap each at
  ~10–15 KB via `img2datauri.py --max-bytes 12000`. Seedance downsamples
  references anyway, so small refs still steer identity/style — with weaker fine
  detail. This smallness is an agent-tooling limit, **not** a model limit.

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
with a `profile.md` (the character bible). Its **reference images live in S3**
(`media/<name>/reference/`), not in git. That skill reads the profile, presigns
its fixed reference set into Replicate URLs, and composes the prompt so the
output stays on-model. This engine skill is character-agnostic.

- **Fred** — recurring illustrated character (the "Gays of Hudson" series).
  Skill: `.claude/skills/fred/`. Reference set: S3 `media/fred/reference`.

### Adding a new character

1. `.claude/skills/<name>/SKILL.md` — copy the Fred skill as a template and
   rewrite the prompt template + guardrails for the new character.
2. `.claude/skills/<name>/profile.md` — the character bible (mirror Fred's
   sections: at-a-glance, face, body, wardrobe, art style, voice, checklist).
3. Upload the character's images to S3 with `<name>/scripts/sync_reference_set.sh`
   (mirror Fred's): the full **originals** archive to `media/<name>/originals/`
   and the curated, numbered **reference** set to `media/<name>/reference/`, kept
   separate and named `<name>_<index>.webp`.
4. Videos save to S3 `media/<name>/output/`. No change to this engine skill is needed.

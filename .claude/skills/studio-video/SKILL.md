---
name: studio-video
description: Generate videos on demand with ByteDance Seedance 2.0 via the Replicate MCP — the engine for any text-to-video / image-to-video / character-video request. Use whenever the user wants to create, generate, or render a video, clip, animation, or motion piece (with optional native audio, first/last-frame images, or reference images/videos/audio). Covers the model input schema, the create-then-poll flow, output naming, and how images reach Replicate (presigned S3 URLs). Part of the studio-* family: pair with studio-prompt to author the prompt and studio-character for on-model character videos.
---

# studio-video — Seedance 2.0 video generation

The rendering engine of the **`studio-*`** family. Generate videos by creating a
Replicate prediction against **`bytedance/seedance-2.0`**
(<https://replicate.com/bytedance/seedance-2.0>) through the **Replicate MCP
server**, polling it, and saving the output MP4 to S3. There is no build step —
the "work" is the MCP call, the poll, and the download.

The family:
- **`studio-prompt`** — author the prompt as structured JSON (camera / subject /
  action / scene / lighting / style / audio, multi-shot timelines). Its `input`
  object drops straight into the call below. Use it for tight or repeatable
  control; plain prose is fine for a quick one-off.
- **`studio-character`** — for a video of a known/recurring character: it
  supplies the character's bible and the reference images this engine requires.
  **FIRST load `studio-character`** — never generate a character from a text
  prompt alone (see "Reference images are MANDATORY" below).
- **`s3`** — the `xharness-assets` asset store references and outputs live in.

## The model: `bytedance/seedance-2.0`

Multimodal video generation with **native audio**, multimodal reference inputs
(images / video / audio), and intelligent duration control. Output is a single
video file URL.

### Input schema

| Field | Type | Default | Notes |
|---|---|---|---|
| `prompt` | string (**required**) | — | Max 4000 chars; keep under ~600 English words. Put **spoken dialogue in double quotes** to drive audio. For tight camera/subject/scene control, a multi-shot timeline, or reusable templates, author it as structured JSON via the **`studio-prompt`** skill and pass its `input` here. |
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

## Prompt approval gate (MANDATORY)

**Before submitting any prompt to the model, show the user the exact final
prompt text and wait for their explicit approval. Do not call
`create_models_predictions` until they say yes.** Re-approve after any edit to
the prompt. The gate covers the prompt sent to the model — the surrounding steps
(presigning references, downloads, uploads, polling) do not need approval. This
keeps output on-brief and avoids failed/billed renders.

## Content filter (E005) — it's nudity wording, not strength

Seedance's filter can reject a job with **error E005** ("input or output flagged
as sensitive"). For muscular characters the trigger is **nudity / undress
language**, not strength or build:

- **Fine:** strong, muscular, broad-shouldered, strong arms, athletic, tank top,
  fitted shirt — describe the build all you like, as long as he's dressed.
- **Trips E005:** "naked", "nude", "shirtless", "bare-chested", "bare skin",
  "undressed", "topless", or any variation. Never use these — always name a
  garment and let the reference images carry the rest.

If a render still hits E005 with a fully-clothed prompt, the **reference images**
can be the flag: reference frames showing a lot of skin (bare arms/chest) pushed
through a photoreal prompt sometimes flag on the *output*. Swap in more-clothed
reference frames (e.g. button-shirt slots) and resubmit — that resolved it in
practice. A clothed-wardrobe + face/hair + scene + dialogue prompt passes.

## Submit with FRESH presigned URLs minted in code (MANDATORY)

**Never hand-paste presigned reference URLs into a prediction call, and never
reuse presigned URLs across calls.** They are ~2 KB each, expire, and a single
mistyped character yields a 400/expired fetch and a dead (often billed) render.
Instead, **mint fresh presigned URLs from code at the moment you submit**, using
the existing presign code, and submit in the same step.

Use the helper — it presigns the character's reference set fresh and POSTs the
prediction directly to the Replicate HTTP API (needs `REPLICATE_API_TOKEN`), so
no URL passes through the agent context:

```bash
# input.json = the built `input` object WITHOUT reference_images
#   (studio-prompt: build_prompt.py prompt.json --emit input  → the .input object)
set -a; . ./.env; set +a
uv run .claude/skills/studio-video/scripts/submit_prediction.py \
  --input-file input.json --character <character> --slots 1,2,3,6 --poll
```

The helper always mints references fresh (it deletes any `reference_images` baked
into the input file first). `--slots` picks which reference numbers map to
`[Image1..N]` in order; omit it to use the whole set. Only fall back to the MCP
`create_models_predictions` tool for a job with no reference images at all.

## How to generate a video (MCP fallback, no references)

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
mkdir -p output/<character>
NAME="$(date +%Y-%m-%d_%H-%M-%S)_<slug>.mp4"
curl -sL "<output_url>" -o "output/<character>/$NAME"

# 2) upload the staged file to S3 (media/<character>/output/) — s3 skill
uv run .claude/skills/s3/scripts/s3_upload.py \
  --folder <character>/output "output/<character>/$NAME"
```

Report the `s3://` URI that `s3_upload.py` prints (add `--presign` for a
shareable HTTPS link). The local `output/<character>/` copy is just staging; S3 is the
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
alone drifts off-model. If you are about to call the model with only a `prompt`
for a character, STOP and load **`studio-character`** first.

- Seedance 2.0 accepts up to **9** `reference_images`. Reference them in the
  prompt as `[Image1]`, `[Image2]`, …
- Each character keeps a **fixed, numbered reference set in S3** (at
  `media/<character>/reference/`), used in full on every generation so identity
  stays locked without re-picking. **`studio-character`** hands you ordered
  presigned URLs for it (`character.py refs <name> --presign`); under the hood
  that is `s3_presign.py --folder <character>/reference` (below).
- `reference_images` **cannot** be combined with `image` / `last_frame_image`.

### How image files reach Replicate (presigned S3 URLs)

Replicate accepts a file input as a URL or an inline data URL. Since references
and outputs live in **S3**, the primary path is a **presigned HTTPS URL**: the
object stays private, Replicate fetches it via a short-lived signed URL, and only
a short URL (never the bytes) enters the agent context. No `REPLICATE_API_TOKEN`
is needed for references.

```bash
# References for a character — ordered presigned URLs (via studio-character)
uv run .claude/skills/studio-character/scripts/character.py refs <character> --presign --json > refs.json
# equivalently, straight from the s3 skill:
uv run .claude/skills/s3/scripts/s3_presign.py --folder <character>/reference --json > refs.json
# -> [{ "key": "media/<character>/reference/<character>_1.webp", "url": "https://..." }, ...]
# Pass the .url values as reference_images; <character>_1 -> [Image1], <character>_2 -> [Image2], ...

# After rendering: upload the finished MP4 to S3 (s3 skill)
uv run .claude/skills/s3/scripts/s3_upload.py --folder <character>/output output/<character>/<name>.mp4
```

Fallbacks for ad-hoc **local** images not in S3 (the Replicate-side helpers live
beside this skill):

```bash
# Local image -> HTTP URL via Replicate Files API (needs REPLICATE_API_TOKEN; see .env)
uv run .claude/skills/studio-video/scripts/upload_to_replicate.py <img>... --json > refs.json

# No token? Local image -> small inline data URL (downscale/recompress to fit --max-bytes)
uv run .claude/skills/studio-video/scripts/img2datauri.py <img>... --max-bytes 12000 --json > refs.json
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
  S3, so a presign hands Replicate full-size images via signed URLs. No token, no
  base64. Use this for any character reference set.
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

Characters are **data, not skills** — a single **`studio-character`** skill
manages them all, and each one is an S3 record (`media/<name>/` with a
`profile.md` bible, a numbered `reference/` set, and `output/`). To generate an
on-model character video, load **`studio-character`**: it reads the bible and
hands you the fixed reference set as ordered presigned URLs; this engine skill is
character-agnostic. A character's rendering style is chosen per video (realistic
by default, or an optional stylized look from its bible §5), not fixed by the
engine.

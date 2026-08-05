---
name: studio-prompt
description: Author Seedance 2.0 prompts as structured JSON. Use whenever a video request wants tight, repeatable control over camera / subject / action / scene / lighting / style / audio, a multi-shot timeline, or a reusable prompt template. Assembles + validates the JSON (one camera move, no bare "fast", no camera verbs in the action, routes technical fields to the real API params) and hands the result to the `studio-video` engine to render. A prompting technique, not a separate model.
---

# studio-prompt — Seedance 2.0 JSON prompting

**JSON prompting is a way to WRITE the prompt, not a separate model or API mode.**
Seedance's `prompt` field is a plain **text string**. "JSON prompting" means
serializing a structured object *into that string* — the model reads structured
text consistently, which makes camera / subject / action / style controllable and
prompts reusable. Rendering is still done by the **`studio-video`** engine
skill (the Replicate MCP call + poll + save-to-S3); this skill only owns *how
the prompt is authored*.

Use this skill when the user wants precise, repeatable control, a multi-shot
timeline, or a template they can tweak. For a quick one-off, plain prose through
`studio-video` is fine — don't force JSON on everything.

> **Character videos:** JSON controls the *words*; it does **not** replace
> reference images. If the request names a known character (e.g. Fred), still
> load **`studio-character`** and pass its `reference_images` — identity comes
> from references, motion/framing from this JSON. Reference them in the text as
> `[Image1]`, `[Image2]`, … inside the relevant JSON field.

## The one rule that shapes everything: text is TEXT

The model does not receive a JSON document over a typed API — it receives the
**serialized string**. So the JSON's job is human/agent legibility and
consistent structure; the model still reads it top-to-bottom as text. Two
consequences drive the whole schema:

1. **Subject + action lead.** The first ~20–30 words carry the most weight.
   Put `subject` and `action` first. (Some third-party guides push a
   *camera-first* order — ByteDance's own guidance and most others disagree, and
   so do we. `build_prompt.py` always emits subject/action first.)
2. **Technical fields are NOT prompt text.** `aspect_ratio`, `duration`,
   `resolution`, `seed`, `generate_audio` are **real Replicate input params** on
   `bytedance/seedance-2.0`. They belong in the API `input`, not baked into the
   prompt string. The helper routes them for you.

## Schema

Author a single JSON object. Creative blocks become the serialized prompt; the
`technical` block is split off to the API params.

```json
{
  "subject":  "WHO / WHAT is in frame — concrete, visual (wardrobe, age, build).",
  "action":   "ONE clear thing they do, concrete verbs. Subject motion only.",
  "scene":    "Where + when + atmosphere (location, time of day, weather, haze).",
  "camera":   { "shot": "medium", "movement": "slow push-in", "lens_mm": 35, "speed": "slow" },
  "lighting": "Physical light setup (key/rim/practical, colour, direction).",
  "style":    "Aesthetic + medium (film tone, grade, grain, animation style).",
  "audio":    "Named sound: ambience + SFX. Music mood if wanted.",
  "dialogue": ["Spoken lines — quoted strings drive native lip-synced audio."],
  "negative": "What to AVOID — jitter, bent limbs, temporal flicker, extra fingers.",
  "technical": {
    "aspect_ratio": "16:9",
    "duration": 6,
    "resolution": "1080p",
    "generate_audio": true,
    "seed": 12345
  }
}
```

### Field notes

| Field | Goes to | Notes |
|---|---|---|
| `subject` | prompt | Lead block. Visual, not vibes. No camera verbs. |
| `action` | prompt | One action. **Subject** motion — camera motion goes in `camera`. |
| `scene` | prompt | Environment + atmosphere. |
| `camera.shot` | prompt | Shot type: wide / medium / close / extreme close / over-shoulder. |
| `camera.movement` | prompt | **Exactly one** move (see list). Stacking degrades output. |
| `camera.lens_mm` | prompt | Focal length, e.g. `35`, `85`. Optional. |
| `camera.speed` | prompt | Qualify it — never bare `"fast"`. |
| `lighting` | prompt | Physical setup. |
| `style` | prompt | Medium + grade. `"cinematic"` is fine here (it's a style word, not filler). |
| `audio` | prompt | Name sounds explicitly; the model only adds audio you direct. |
| `dialogue` | prompt | Array of quoted lines → native synced speech. |
| `negative` | prompt (`avoid`) | **Seedance has NO negative_prompt param** — it stays in the prompt text as an `avoid` key. |
| `technical.*` | **API input** | Split off to the Replicate params. |

Camera movements (pick **one**): `push-in` · `pull-out` · `pan` · `tilt` ·
`tracking` · `orbit` · `aerial/drone` · `handheld` · `crane` · `rack focus` ·
`static/hold`.

### Multi-shot: timeline mode

For a sequence, supply a `shots` array instead of a single `action`. Globals
(`subject`, `style`, `audio`, `lighting`) stay top-level; each shot carries its
own beat. Keep total to `technical.duration` and give ~3 beats per 8s.

```json
{
  "subject": "A detective in a long coat",
  "style": "Neo-noir, teal/amber grade, 2.39:1",
  "shots": [
    { "t": "0s", "shot": "wide",   "camera": "static",       "description": "Stands at the end of a rain-slicked street" },
    { "t": "3s", "shot": "medium", "camera": "slow dolly in", "description": "Camera closes in from behind" },
    { "t": "6s", "shot": "close",  "camera": "hold",          "description": "Rain beads on his collar; he exhales" }
  ],
  "technical": { "duration": 8, "aspect_ratio": "21:9" }
}
```

## Approve before sending; keep characters clothed; style is optional

- **Show the user the final prompt and get approval before it is rendered.** The
  render engine (`studio-video`) will not submit a prompt to the model until the
  user has approved the exact text; author here, then hand off for that gate.
- **Describe characters clothed — the trigger is nudity wording, not strength.**
  It is fine to call a character strong, muscular, broad-shouldered, with strong
  arms, in a tank top or fitted shirt. What trips Seedance's E005 content filter
  is **nudity/undress wording** — "naked", "nude", "shirtless", "bare-chested",
  "bare skin", "undressed", or any variation. Never use those; always name a
  garment (§4 of the character's bible) and let the reference images carry the
  rest of the build. See the content-filter note in `studio-video`.
- **Rendering style is a per-video choice, not baked into a character.** A
  character's bible describes WHO they are, independent of medium; the look
  (realistic vs. an illustrated/stylized treatment) is set per video in the
  `style` field. Default to realistic unless a style is requested — don't copy a
  character's signature art style into every prompt automatically. Characters
  that ship optional style presets (e.g. Fred's §5) give ready-to-paste `style`
  text for each option.

## Rules the validator enforces (and why)

These come straight from the Seedance prompt guides. `build_prompt.py` warns on
each; treat warnings as author feedback, fix them before rendering.

- **One camera move.** `"dolly in and orbit"` → chaos. One shot type + one move.
- **No bare `"fast"`.** Qualify it: `"fast whip-pan"`, `"quick 1s push-in"`.
- **No camera verbs in `subject`/`action`.** Those blocks describe the subject;
  camera direction lives in `camera`.
- **No vague adjectives** (`amazing`, `epic`, `stunning`, `beautiful`…). The
  model ignores mood words — describe what's observable instead.
- **60–100 words** of real content is the sweet spot for a single shot. JSON
  keys/structure don't count against you; padding prose does.
- **Technical fields** never sit in the prompt text — the helper routes them, and
  drops invented ones (`fps`, `creativity`, `lock_identity`…) that Replicate
  doesn't accept.

## Workflow

### 1) Assemble + validate with the helper

The script takes your object (file, stdin, or `--json`), validates the rules,
splits `technical` off to the API params, and emits `{prompt, input, warnings}`.

```bash
# from a file
uv run .claude/skills/studio-prompt/scripts/build_prompt.py prompt.json

# inline, only want the ready-to-use Replicate input object
uv run .claude/skills/studio-prompt/scripts/build_prompt.py --json '{ ... }' --emit input

# override a couple of technical fields without editing the file
uv run .claude/skills/studio-prompt/scripts/build_prompt.py prompt.json \
  --aspect-ratio 9:16 --duration 8 --resolution 1080p
```

Output shape:

```json
{
  "prompt": "{ …serialized creative JSON… }",
  "input":  { "prompt": "…same string…", "aspect_ratio": "16:9", "duration": 6, "resolution": "1080p", "generate_audio": true },
  "timeline": false,
  "warnings": [ … ]
}
```

Flags: positional `source` (file or `-` for stdin) · `--json` · creative
overrides (`--subject/--action/--scene/--style/--lighting/--audio/--negative`,
`--camera-movement/--camera-shot/--lens-mm`) · technical overrides
(`--aspect-ratio/--duration/--resolution/--seed/--no-audio`) · `--emit
both|prompt|input` · `--compact` (single-line prompt) · `--strict` (non-zero exit
on any warning). Invalid enums / durations exit non-zero as **errors**.

### 2) Render via the `studio-video` engine

The `input` object is ready to pass to the Replicate MCP `create_models_predictions`
call (`model_owner: "bytedance"`, `model_name: "seedance-2.0"`). Follow the
**`studio-video`** skill for the actual create → poll → download →
save-to-S3 flow, and for how reference images / first-frame images attach:

- **Character or reference-image job:** add `reference_images` to the `input`
  (per `studio-video`), and reference them in the JSON text as `[Image1]`, …
  Remember `reference_images` **cannot** be combined with `image` /
  `last_frame_image`.
- **First/last-frame job:** add `image` (and optional `last_frame_image`).
- Everything else about polling, output naming, and S3 upload is unchanged —
  this skill only changed how `prompt` was authored.

## When NOT to use JSON

- A single simple clip with no fussy camera/lighting needs → plain prose prompt
  through `studio-video` reads just as well and is faster to write.
- When identity is the whole point → the win is **reference images**, not JSON.
  Use JSON for the surrounding motion/framing, references for the character.

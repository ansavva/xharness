---
name: fred
description: Generate on-model videos of Fred, the illustrated "Gays of Hudson" character, using Seedance 2.0 via the Replicate MCP. Use whenever the user asks for a video, clip, or animation "of Fred", references the Fred character, or wants a new scene featuring him. Wires Fred's character bible and reference illustrations into the video prompt so the output stays recognizable (mustache, leather, pen-and-ink style, Hudson Valley setting). Runs on the `seedance-video` engine skill.
---

# Fred video skill

Generate videos of **Fred** — the mascot/narrator of the illustrated "Gays of
Hudson" series — that stay on-model. Fred only reads as Fred inside a specific
look (pen-and-ink crosshatch, horseshoe mustache, black leather, V-taper,
Hudson Valley setting). This skill enforces that.

This skill supplies Fred's identity; the generation mechanics (model schema,
create-then-poll flow, output naming, how references reach Replicate) live in the
**[`seedance-video`](../seedance-video/SKILL.md)** engine skill — read it for the
call/poll details.

> **MANDATORY:** every Fred video MUST pass Fred's reference set in the
> `reference_images` input — never generate from the text prompt alone (it
> drifts off-model). Not optional. The set is **fixed** (see "The reference set"
> below): you pass the same numbered images every time, so there's nothing to
> re-pick per scene.

## Source of truth

- **Character bible:** [`profile.md`](profile.md) — read it before writing any
  prompt. It defines his face, mustache (non-negotiable), body, wardrobe, art
  style, voice, and a consistency checklist.
- **Images (S3, not git):** bucket `xharness-assets`, prefix `media/`.
  - **Reference set** — `media/fred/reference/` (`fred_1.webp … fred_9.webp`):
    the fixed, curated set used on **every** generation.
  - **Originals archive** — `media/fred/originals/` (`fred_1.webp … fred_26.webp`):
    all source illustrations, kept **separate** from the reference set (an archive
    to re-curate from; not used at generation time).
  - **Renders** — `media/fred/output/` (also staged locally under `output/fred/`,
    git-ignored).

## The reference set

Fred always generates from the **same nine reference images** so his identity
stays locked without re-choosing references each run. They live in S3 at
`media/fred/reference/`, named `fred_1`–`fred_9` (each `fred_N` → prompt slot `[ImageN]`):

| file | What it anchors |
|---|---|
| fred_1 | Face close-up — mustache, hair, brow, chin |
| fred_2 | Shirtless front (meditation) — face + torso, V-taper, chest hair |
| fred_3 | Full body, shirtless + jeans — proportions |
| fred_4 | Seated, white tee + leather pants — canonical wardrobe |
| fred_5 | Walking, button shirt + jeans — clothed full body + demeanor |
| fred_6 | Porch reading, shirtless + leather — pen-and-ink style |
| fred_7 | Driving, white tank — arms/forearms + 3/4 face |
| fred_8 | City, white button shirt + leather — clothed full body (alt) |
| fred_9 | Shaving close-up — mustache detail |

To (re)build and upload the S3 folders, run the one-time migration (uploads the
originals archive **and** the curated reference set; renames everything to
`fred_<index>.webp`):

```bash
.claude/skills/fred/scripts/sync_reference_set.sh              # both folders
.claude/skills/fred/scripts/sync_reference_set.sh --reference-only   # just the set
```

(Requires an AWS login — run `aws login` first; see the `s3` skill. Edit
`REF_MAP` in that script to change which originals make up the reference set.)

## Workflow

1. **Read [`profile.md`](profile.md)** (skim §7 Consistency Checklist + §2/§4/§5
   at minimum). Do not generate from memory.
2. **Presign the reference set from S3 for Replicate.** Always use the whole
   numbered set — no per-scene selection:
   ```bash
   # presign all of media/fred/reference as ordered HTTPS URLs (bytes stay in S3)
   uv run .claude/skills/s3/scripts/s3_presign.py --folder fred/reference --json > refs.json
   ```
   Pass every `.url` as `reference_images` (Seedance accepts up to 9), and cite
   them in the prompt as `[Image1] … [Image9]` (`fred_1`→`[Image1]`, …). The list
   is returned in `fred_1..fred_9` order; only the short signed URLs enter the
   agent context, never the image bytes.
   - Remember: `reference_images` **cannot** be combined with a first-frame
     `image`. For an exact starting frame instead of character transfer, use
     `image` and drop `reference_images`.
   - The bucket is private; presigned URLs default to a 1 h expiry — fine for a
     render. Run `aws login` if the s3 script reports it can't resolve creds.
3. **Write the prompt** using the template below, translating the profile into
   concrete visual/audio direction. Put any spoken line in **double quotes** so
   Seedance generates the audio in Fred's voice.
4. **Generate** with the Replicate MCP `create_models_predictions`
   (`model_owner: "bytedance"`, `model_name: "seedance-2.0"`, no `Prefer: wait`).
   Poll `get_predictions` until `succeeded`, then save the MP4 to S3 under
   `media/fred/output/` (see [`seedance-video`](../seedance-video/SKILL.md) →
   "Output location" for the download-then-upload pattern and naming).
5. **Verify against the checklist** (§7 of the profile): mustache present and
   full, wavy swept-back hair, small/narrow chin, leather trousers/boots,
   V-taper (not over-bulked), pen-and-ink crosshatch rendering, detailed Hudson
   Valley/NYC background, no beard/glasses/hat. Regenerate if any hard cue is off.

## Prompt template

Compose the prompt from these blocks (fill in the scene specifics):

```
Pen-and-ink crosshatch illustration animated in the vintage underground-comix /
editorial-engraving style, high-contrast black and white on aged paper.
Fred — a tall, heavily-muscled man in his late 30s with a full dark horseshoe
mustache, wavy dark hair swept up and back, deep-set light eyes under heavy
brows, a small narrow softly-rounded chin, and broad shoulders tapering to a
narrow waist (lean athletic V-taper, not bulky) — matching [Image1]–[Image9].
He wears [black leather trousers with a wide belt and leather boots + one of:
white ribbed tank / white tee / rolled-sleeve utility shirt / bare-chested].
SETTING: [specific Hudson Valley or NYC location — Warren St., The Half Moon,
a subway car, a clapboard porch, etc.], drawn with obsessive architectural detail.
ACTION: [what he does over the clip].
Fred says: "[short, present-tense, first-person line — warm, earnest, dry innuendo]"
```

### Style guardrails (always include / never violate)

- **Always:** ink crosshatch rendering, full horseshoe mustache, small narrow
  chin, leather, lean athletic V-taper, richly detailed specific location,
  warm/wry demeanor.
- **Never:** photorealism, a shrunken/thin or absent mustache, a broad or jutting
  chin, slicked-flat or short hair, bodybuilder bulk that loses the narrow waist,
  athleisure/suits, empty backgrounds, beard, glasses, hat, or jewelry beyond a
  plain watch.

### Voice for dialogue

Short declarative sentences, present tense, first person, plain words, often
addressed to "boys" / "those gays". Sincerity is the joke — no self-irony.
Examples of register: warm community invites and deadpan double entendres
delivered straight-faced.

## Defaults

- `aspect_ratio`: `1:1` (the series' native square) unless the user asks for
  `16:9` / `9:16`.
- `resolution`: `1080p`. `duration`: `5` (or `-1` for the model to choose).
- `generate_audio`: `true` when there's a spoken line or ambient scene.

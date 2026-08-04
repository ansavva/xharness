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

> **MANDATORY:** every Fred video MUST pass Fred's reference images in the
> `reference_images` input — never generate from the text prompt alone (it
> drifts off-model). Not optional. See the `seedance-video` skill →
> "Reference images are MANDATORY" and "How image files reach Replicate" for the
> base64/data-URL mechanics, the ≤ 256 KB rule, and the full-res HTTP-URL path.

## Source of truth

- **Character bible:** [`profile.md`](profile.md) — read it before writing any
  prompt. It defines his face, mustache (non-negotiable), body, wardrobe, art
  style, voice, and a consistency checklist.
- **Reference illustrations:** [`images/`](images/) — 26 reference images. Prior
  renders are saved under `output/fred/` at the repo root (git-ignored).

## Workflow

1. **Read [`profile.md`](profile.md)** (skim §7 Consistency Checklist + §2/§4/§5
   at minimum). Do not generate from memory.
2. **Pick reference images.** Choose 2–4 from [`images/`](images/) that match the
   angle/wardrobe/framing of the scene. Pass them as `reference_images` (up to 9)
   so Fred stays consistent, and cite them in the prompt as `[Image1]`, `[Image2]`.
   Convert local files to a Replicate-ready form first:
   - **If `REPLICATE_API_TOKEN` is set** (see `.env`), upload full-resolution and
     pass HTTP URLs — best quality, no context cost:
     ```bash
     uv run .claude/skills/seedance-video/scripts/upload_to_replicate.py \
       .claude/skills/fred/images/<one>.webp .claude/skills/fred/images/<two>.webp --json > refs.json
     ```
   - **Otherwise** shrink to small inline data URLs (~10–15 KB each):
     ```bash
     uv run .claude/skills/seedance-video/scripts/img2datauri.py \
       .claude/skills/fred/images/<one>.webp .claude/skills/fred/images/<two>.webp --max-bytes 12000 --json > refs.json
     ```
   Then pass the resulting URLs/`data:` strings as `reference_images`.
   - Remember: `reference_images` **cannot** be combined with a first-frame
     `image`. For an exact starting frame instead of character transfer, use
     `image` and drop `reference_images`.
3. **Write the prompt** using the template below, translating the profile into
   concrete visual/audio direction. Put any spoken line in **double quotes** so
   Seedance generates the audio in Fred's voice.
4. **Generate** with the Replicate MCP `create_models_predictions`
   (`model_owner: "bytedance"`, `model_name: "seedance-2.0"`, no `Prefer: wait`).
   Poll `get_predictions` until `succeeded`, then download the MP4 into
   `output/fred/` (see [`seedance-video`](../seedance-video/SKILL.md) for the full
   call/poll pattern and naming).
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
narrow waist (lean athletic V-taper, not bulky) — matching [Image1] and [Image2].
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

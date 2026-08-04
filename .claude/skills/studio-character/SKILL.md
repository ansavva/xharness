---
name: studio-character
description: Manage on-model characters (like "Fred") for video generation — create, update, list, and load a character whose profile bible and reference images live in the xharness-assets S3 bucket. Use whenever a video request names a known/recurring character, or the user wants to add, edit, curate, or inspect one. A character is DATA (an S3 record under media/<name>/), not a per-character skill: this one skill manages them all and wires a character's profile + reference set into the studio-prompt / studio-video pipeline so output stays recognizable.
---

# studio-character

Characters are **data, not skills.** Instead of a skill per character, every
character is an S3 record managed by this one skill, used by the video pipeline
(`studio-prompt` to author the prompt, `studio-video` to render). Part of the
**`studio-*`** family:

- **`studio-character`** (this skill) — owns character identity: the bible + refs.
- **`studio-prompt`** — authors the Seedance prompt as structured JSON.
- **`studio-video`** — renders it via Seedance 2.0 on Replicate, saves to S3.

> **MANDATORY for any character video:** pass the character's reference set in
> `reference_images` — never generate from the text prompt alone (it drifts
> off-model). Identity comes from the references + bible; motion/framing from the
> prompt.

## Where a character lives (S3)

Each character is a record under `media/<name>/` in the **`xharness-assets`**
bucket (the generic **`s3`** skill is the storage layer; auth is your `aws
login`). The layout matches the existing media tree:

```
media/<name>/profile.md      the character bible — SOURCE OF TRUTH
media/<name>/reference/       curated set, <name>_1.<ext> … <name>_N.<ext>
                              (used IN FULL on every generation)
media/<name>/originals/       optional archive to re-curate the set from
media/<name>/output/          rendered videos (written by studio-video)
```

`profile.md` is canonical in S3 (edit it via this skill). A **blank template** is
in [`templates/profile.md`](templates/profile.md); a **fully worked example** is
in [`examples/fred/profile.md`](examples/fred/profile.md) — read it before
writing a new bible.

## The management tool

[`scripts/character.py`](scripts/character.py) is the CRUD + load layer. It reuses
the **`s3`** skill's `s3_common.py` (the AWS-login-bridged boto3 client, the
`media/` key mapping, natural sort) — one storage layer, one auth path, no bytes
in the agent context. Requires an `aws login` (see the `s3` skill).

```bash
CH=.claude/skills/studio-character/scripts/character.py

uv run $CH list                                  # every character
uv run $CH show fred                             # print fred's profile.md (from S3)
uv run $CH create nova --from-profile /tmp/nova.md   # new character record
uv run $CH set-profile nova /tmp/nova.md         # replace the bible
uv run $CH add-refs nova /tmp/nova/*.webp        # add refs, numbered nova_1..N
uv run $CH refs fred --presign --json            # generation-time: ordered signed URLs
uv run $CH refs fred --dest /tmp/fred-refs       # or download the set locally
```

`add-refs` numbers new images `<name>_<n>` continuing after the current highest
index; `--replace` renumbers from 1 (overwrites the set in place), `--start N`
sets an explicit start. The number is the `[ImageN]` slot the prompt cites.

## Generating a character video (the full flow)

1. **Load the bible.** `uv run $CH show <name>` — read it (esp. the §7
   consistency checklist and signature features). Don't generate from memory.
2. **Get the reference set as ordered presigned URLs.** These go straight into
   the prediction's `reference_images` — the bucket stays private, only short
   URLs enter context, no `REPLICATE_API_TOKEN` needed:
   ```bash
   uv run $CH refs <name> --presign --json > refs.json
   # -> [{ "key": "media/<name>/reference/<name>_1.webp", "url": "https://..." }, ...]
   ```
   Pass the `.url` values as `reference_images` (Seedance accepts up to 9) and
   cite them in the prompt text as `[Image1]…[ImageN]` (`<name>_1` → `[Image1]`).
   `reference_images` **cannot** be combined with a first-frame `image`.
3. **Author the prompt.** Translate the bible into concrete visual/audio
   direction — ideally with **`studio-prompt`** (structured JSON): the character's
   look in `subject`, the scene action in `action`, and cite `[Image1]…` inside
   `subject`. Put any spoken line in **double quotes** so Seedance generates the
   audio in-character.
4. **Render + save** via **`studio-video`** (Replicate `create_models_predictions`,
   poll, download, upload the MP4 to `media/<name>/output/`). See that skill.
5. **Verify against §7** of the bible; regenerate if any hard cue is off.

## Adding a new character

1. Write the bible from [`templates/profile.md`](templates/profile.md) (use
   [`examples/fred/profile.md`](examples/fred/profile.md) as the gold standard).
2. `uv run $CH create <name> --from-profile <your-bible.md>`.
3. `uv run $CH add-refs <name> <curated images…>` — the numbered set used on
   every generation. Archive all source images under `media/<name>/originals/`
   via the `s3` skill if you want a re-curation pool.

No new skill directory — ever. The character is now usable by the whole pipeline.
(Names are lowercase `[a-z0-9_-]`; `misc` is reserved for non-character output.)

## Fred

Fred is the worked example (the "Gays of Hudson" series). His full record already
lives in S3: `media/fred/profile.md`, `media/fred/reference/fred_1..9.webp`, and
`media/fred/originals/`. His bible is committed at
[`examples/fred/profile.md`](examples/fred/profile.md) as the template gold
standard; the reference-set composition is documented in
[`examples/fred/README.md`](examples/fred/README.md). Use him with the normal
flow: `uv run $CH show fred`, `uv run $CH refs fred --presign`.

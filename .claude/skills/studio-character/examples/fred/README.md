# Fred — reference example

Fred is the worked example for `studio-character`: the recurring illustrated
character of the "Gays of Hudson" series. His bible is [`profile.md`](profile.md)
— the gold-standard fill-in for [`../../templates/profile.md`](../../templates/profile.md).

Fred reads as Fred only inside a specific look: pen-and-ink crosshatch, full
horseshoe mustache, black leather, lean athletic V-taper, small narrow chin, a
detailed Hudson Valley / NYC setting. See §5 and §7 of the bible.

## His S3 record (already populated)

Fred is a normal character record in the `xharness-assets` bucket — nothing to
migrate:

```
media/fred/profile.md                     the bible (canonical; mirror of profile.md here)
media/fred/reference/fred_1..9.webp        curated set, passed on every generation
media/fred/originals/fred_1..26.webp       full source archive
media/fred/output/                          renders
```

Use him with the normal flow:

```bash
CH=.claude/skills/studio-character/scripts/character.py
uv run $CH show fred                    # bible from S3
uv run $CH refs fred --presign --json   # ordered signed URLs -> reference_images
```

## The curated 9-image reference set

Fred always generates from the **same nine images**, passed IN FULL as
`reference_images` every time. Order defines the `[Image1]…[Image9]` slots
(`fred_1` → `[Image1]`, …).

Each image carries a same-named **`.txt` sidecar** in S3
(`media/fred/reference/fred_N.txt`) describing what it contains, so the set is
self-documenting — no need to consult this README to know a slot's contents.
Read them straight from S3:

```bash
CH=.claude/skills/studio-character/scripts/character.py
uv run $CH refs fred --captions        # each slot + its sidecar caption
```

`refs --presign` / `--dest` only ever return the image objects; the `.txt`
sidecars are metadata and are filtered out of the reference frames. To re-curate,
re-upload from the originals archive with
`character.py add-refs fred <images…> --replace` (renumbers from 1), and add a
matching `fred_N.txt` per image. A labeled contact sheet of any folder can be
regenerated with [`../../scripts/contact_sheet.py`](../../scripts/contact_sheet.py):

```bash
CS=.claude/skills/studio-character/scripts/contact_sheet.py
uv run $CS --character fred --folder originals  --out .claude/skills/studio-character/examples/fred/originals_contact.png
uv run $CS --character fred --folder reference  --out .claude/skills/studio-character/examples/fred/reference_contact.png
```

The current sheets live beside this file: [`originals_contact.png`](originals_contact.png)
(the 26-image archive) and [`reference_contact.png`](reference_contact.png) (the
curated 9). Refresh them whenever the sets change.

## Defaults for Fred videos

- `aspect_ratio`: `1:1` (the series' native square) unless asked otherwise.
- `resolution`: `1080p`; `duration`: `5` (or `-1` to let the model choose).
- `generate_audio`: `true` when there's a spoken line or ambient scene.
- Voice: short declarative present-tense first-person lines, warm and wry, often
  addressed to "boys" / "those gays"; sincerity is the joke. Put lines in double
  quotes in the prompt.

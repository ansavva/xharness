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
(`fred_1` → `[Image1]`, …):

| slot | file | What it anchors |
|---|---|---|
| 1 | fred_1 | Face close-up — mustache, hair, brow, chin |
| 2 | fred_2 | Shirtless front (meditation) — face + torso, V-taper, chest hair |
| 3 | fred_3 | Full body, shirtless + jeans — proportions |
| 4 | fred_4 | Seated, white tee + leather pants — canonical wardrobe |
| 5 | fred_5 | Walking, button shirt + jeans — clothed full body + demeanor |
| 6 | fred_6 | Porch reading, shirtless + leather — pen-and-ink style |
| 7 | fred_7 | Driving, white tank — arms/forearms + 3/4 face |
| 8 | fred_8 | City, white button shirt + leather — clothed full body (alt) |
| 9 | fred_9 | Shaving close-up — mustache detail |

To re-curate the set, re-upload from the originals archive with
`character.py add-refs fred <images…> --replace` (renumbers from 1).

## Defaults for Fred videos

- `aspect_ratio`: `1:1` (the series' native square) unless asked otherwise.
- `resolution`: `1080p`; `duration`: `5` (or `-1` to let the model choose).
- `generate_audio`: `true` when there's a spoken line or ambient scene.
- Voice: short declarative present-tense first-person lines, warm and wry, often
  addressed to "boys" / "those gays"; sincerity is the joke. Put lines in double
  quotes in the prompt.

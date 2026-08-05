# <NAME> — Character Profile

*Reference bible for on-model video generation. Built from <N> reference images.*
*This is the character's SOURCE OF TRUTH — it lives in S3 (`characters/<name>/profile.md`)*
*and is wired into every generation. Fill every section with concrete, observable detail;*
*avoid mood words. Run `character.py show <name>` on an existing character for a fully worked example.*

> **Describe WHO the character is, independent of medium.** Rendering style
> (realistic vs. an illustrated/stylized look) is a **per-video choice** — put it
> in §5 as optional presets, not as a fixed part of identity. Default to realistic
> unless a style is requested.
> **Keep characters clothed in prose.** Name a garment; strength/build words are
> fine, but "naked / nude / shirtless / bare-chested / undressed" trip the render
> content filter — never use them.

---

## 1. At a Glance

| Attribute | Detail |
|---|---|
| Name | <name> |
| Apparent age | <e.g. mid-30s> |
| Build | <body type in one line> |
| Height read | <how tall they read against the environment> |
| Signature features | <the 2–3 cues that make them instantly recognizable> |
| Home turf | <recurring setting / world> |
| Register | <voice + demeanor in a few words> |
| Rendering style | Chosen per video — see §5 (realistic by default; any stylized look is optional) |

---

## 2. Face — Detailed

Describe overall structure, eyes, eyebrows, nose, the defining feature(s),
mouth/jaw/chin, hair, ears. Be specific about proportions and what must NOT
drift (the recognition-critical cues). One paragraph per feature.

---

## 3. Body Type — Detailed

Silhouette and proportions (the single most reliable cue for redrawing them),
upper body, lower body and hands, posture and body language.

---

## 4. Wardrobe

The core uniform (the repeated, recognizable garments), tops in rough order of
frequency, accessories, and the palette for color. A small, repetitive closet is
what makes a character instantly readable. The character is **always dressed** —
list the garments so prompts can name one.

---

## 5. Rendering — choose per video (optional style)

Identity is style-agnostic; rendering is a per-video choice set in the prompt's
`style` field. Give a **default (usually realistic)** and, if the character has a
signature stylized look, an **optional** preset for it — each with ready-to-paste
`style` text. Also note framing/format and background rules (which apply in
either style). Do NOT force a single art style as part of identity.

---

## 6. Personality and Voice

Who they are and how they behave, then explicit voice notes for dialogue
(sentence length, tense, person, vocabulary, who they address). Put spoken lines
in double quotes in the prompt so Seedance generates the audio.

---

## 7. Consistency Checklist

When generating any new asset, verify:

- [ ] <hard cue 1 — the non-negotiable signature feature>
- [ ] <hard cue 2>
- [ ] <hard cue 3>
- [ ] <wardrobe cue — always dressed>
- [ ] Rendering matches the style chosen in §5 (realistic by default, or an optional style if requested)
- [ ] <environment cue>
- [ ] <what must be ABSENT — common wrong additions>

### Common failure modes to avoid

- <the most common way the model drifts off-model>
- <second failure mode>

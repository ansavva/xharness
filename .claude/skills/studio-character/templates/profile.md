# <NAME> — Character Profile

*Reference bible for on-model video generation. Built from <N> reference images.*
*This is the character's SOURCE OF TRUTH — it lives in S3 (`characters/<name>/profile.md`)*
*and is wired into every generation. Fill every section with concrete, observable detail;*
*avoid mood words. Run `character.py show fred` for a fully worked example.*

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
| Rendering style | <medium: photoreal / pen-and-ink / 3D / anime / …> |

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
frequency, accessories, and the palette for any color renders. A small,
repetitive closet is what makes a character instantly readable.

---

## 5. Art Style Specification

Medium, line, shading, value, composition/format, text treatment, and
backgrounds. This matters as much as the anatomy — the character only reads as
themselves inside this rendering language.

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
- [ ] <wardrobe cue>
- [ ] <rendering-style cue>
- [ ] <environment cue>
- [ ] <what must be ABSENT — common wrong additions>

### Common failure modes to avoid

- <the most common way the model drifts off-model>
- <second failure mode>

---
name: wordgen
description: Generate pronounceable pseudowords that sound real but aren't — good for brand names, product names, coined terms. Supports sound-palette styles (heritage, byzatic) and naming-brief constraints.
argument-hint: "[-n count] [--style plain|heritage|byzatic] [--brand] [--avoid-initial LETTERS] [--no-medical] [--min/--max-syllables N] [--suffix-prob P] [--capitalize] [--pair-with WORD] [--seed N]"
allowed-tools:
  - Bash
---

Generate pronounceable pseudowords — invented words that obey English (and,
in `heritage` style, romance-language) sound patterns so they read as
plausible rather than random gibberish. Useful for brand names, product
names, and coined terms.

Run from the repo root:

```bash
uv run .claude/skills/wordgen/scripts/wordgen.py [options]
```

## Options

- `-n`, `--count` — how many words to generate (default: 10)
- `--style` — sound palette (default: `plain`):
  - `plain` — neutral invented English
  - `heritage` — soft, romance-language flow evoking Spanish/Greek words for
    dawn and first light (Lucero, Vela, Solera, Aurora, Eos): gentle
    consonants, vowel-rich, `-era`/`-ero`/`-ela` endings
  - `byzatic` — smooth and flowing with a woven `z`, after the sample word
    *byzatic*: liquid consonants, a medial z, `-atic`/`-ica`/`-yne` caps
- `--brand` — company-name preset: pairs each word with one of
  **Labs / Works / Solutions / Systems**, capitalizes, and keeps words short
  (max 2 syllables unless overridden)
- `--avoid-initial LETTERS` — discard words starting with any of these letters,
  e.g. `--avoid-initial a` (case-insensitive)
- `--no-medical` — drop clinical / Greek-medical endings (`-os`, `-as`, `-us`,
  `-um`, `-is`) that make a word sound like a diagnosis
- `--min-syllables N` / `--max-syllables N` — syllable bounds (default 2–3)
- `--suffix-prob P` — probability [0-1] of appending a stylistic suffix (default: 0.25)
- `--capitalize` — capitalize the first letter of each word
- `--pair-with WORD` — append a fixed word after each result (repeatable; one
  is chosen at random per word). `--brand` is the shorthand for the four
  standard suffixes
- `--seed N` — seed the RNG for reproducible output

Words print one per line. If `uv` is not installed, tell the user to run
`brew install uv`.

## Examples

```bash
# Neutral invented words
uv run .claude/skills/wordgen/scripts/wordgen.py

# Short, punchy, capitalized brand-style names
uv run .claude/skills/wordgen/scripts/wordgen.py -n 8 --max-syllables 2 --capitalize

# Company names: base word + Labs/Works/Solutions/Systems
uv run .claude/skills/wordgen/scripts/wordgen.py --brand -n 8

# Dawn / first-light heritage names (Spanish/Greek feel)
uv run .claude/skills/wordgen/scripts/wordgen.py --style heritage -n 10 --capitalize

# "byzatic"-flavoured coinages
uv run .claude/skills/wordgen/scripts/wordgen.py --style byzatic -n 10 --capitalize
```

---

## Naming-project context (asavva)

This skill was built for an ongoing company-naming effort. When generating
candidates for that project, apply these standing preferences:

- **Aesthetic:** aperture / light / focus — dawn and first light. The user is
  half Greek Cypriot, half Mexican American; both cultures personify dawn
  (Greek *Eos*, Spanish/Latin *Aurora*, the morning star), so the
  **heritage** style is the primary lane, leaning Spanish-forward.
- **Sonic target:** the smooth, flowing quality of the invented word
  *byzatic* (the `z` sound, the rhythm) — the **byzatic** style captures this.
- **Structure:** short, elegant, easy to say, with a touch of mystery.
  Combined/portmanteau feel (à la Thoughtworks, Starbucks) paired with the
  suffixes **Labs / Works / Solutions / Systems** — use `--brand`.
- **Hard constraints (always pass these for this project):**
  - `--avoid-initial a` — no names starting with "A"
  - `--no-medical` — avoid the clinical Greek `-os`/`-as` endings
- **Bases already in play** (for reference / blending, not generated):
  Lucero, Vela, Solera, Brasa, Reya, Lumbre, Destello.
- **Ruled out:** anything starting with A · medical-sounding Greek endings ·
  Meridian, Compass, Zenith, Aperture (oversaturated) · space/satellite-
  sounding names · clunky portmanteaus.

Recommended invocation for this project:

```bash
uv run .claude/skills/wordgen/scripts/wordgen.py --style heritage --brand \
  --avoid-initial a --no-medical -n 15
```

### Availability lookups (only when explicitly asked)

Do **not** look up names automatically. When — and only when — the user
explicitly asks to check a name, run this workflow for each requested name:

1. **LLC check:** whether the business name is already registered. The user is
   based in **NYC**, so check the **New York State** entity database (NY
   Department of State / Secretary of State business search).
2. **Domain check:** whether the domain is available on **.io**, **.dev**,
   **.com**, and **.ai**.

Report each name with its LLC status and per-TLD domain availability. Use web
search / lookup tools for this step; the generator itself does no network I/O.

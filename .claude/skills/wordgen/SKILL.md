---
name: wordgen
description: Generate pronounceable pseudowords that sound real but aren't — good for brand names, product names, coined terms
argument-hint: "[-n count] [--min-syllables N] [--max-syllables N] [--suffix-prob P] [--capitalize] [--pair-with WORD] [--seed N]"
allowed-tools:
  - Bash
---

Generate pronounceable pseudowords — invented words that obey English sound
patterns so they read as plausible rather than random gibberish. Useful for
brand names, product names, and coined terms.

Run from the repo root:

```bash
uv run .claude/skills/wordgen/scripts/wordgen.py [options]
```

Options:
- `-n`, `--count` — how many words to generate (default: 10)
- `--min-syllables N` — minimum syllables per word (default: 2)
- `--max-syllables N` — maximum syllables per word (default: 3)
- `--suffix-prob P` — probability [0-1] of appending a Latinate suffix like
  `-us`, `-ica`, `-yn`, `-ine` for a coined feel (default: 0.25)
- `--capitalize` — capitalize the first letter of each word
- `--pair-with WORD` — brand mode: append a fixed word after each result,
  e.g. `--pair-with Labs`. Repeatable; one is chosen at random per word
  (e.g. `--pair-with Labs --pair-with Works --pair-with Systems`)
- `--seed N` — seed the RNG for reproducible output

Examples:

```bash
# Ten default words
uv run .claude/skills/wordgen/scripts/wordgen.py

# Short, punchy, capitalized brand-style names
uv run .claude/skills/wordgen/scripts/wordgen.py -n 8 --max-syllables 2 --capitalize

# Company-name mode: base word + suffix
uv run .claude/skills/wordgen/scripts/wordgen.py -n 6 --max-syllables 2 \
  --pair-with Labs --pair-with Works --pair-with Solutions --pair-with Systems

# Latinate/scientific-sounding coinages
uv run .claude/skills/wordgen/scripts/wordgen.py -n 8 --suffix-prob 0.8
```

Words print one per line. If `uv` is not installed, tell the user to run
`brew install uv`.

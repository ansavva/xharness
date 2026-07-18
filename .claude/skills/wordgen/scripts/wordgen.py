# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Generate pronounceable pseudowords that sound real but aren't.

Words are assembled from English phonotactic building blocks — weighted
onset clusters, vowel nuclei, and coda clusters — so the output obeys real
sound patterns and reads as plausible rather than random.

Three sound palettes ("styles") are available:

  plain     — neutral invented English (the default).
  heritage  — soft, romance-language flow evoking Spanish/Greek words for
              dawn and first light (Lucero, Vela, Solera, Aurora, Eos):
              gentle consonants, vowel-rich, -era/-ero/-ela endings.
  byzatic   — smooth and flowing with a woven "z", after the sample word
              *byzatic*: liquid consonants, a medial z, -atic/-ica/-yne caps.

Constraint flags (--avoid-initial, --no-medical) let you steer output for a
specific naming brief, e.g. "nothing starting with A, nothing clinical."
"""
import argparse
import random

# Endings we treat as clinical / Greek-medical sounding, filtered out by
# --no-medical (the -os / -as / -us / -um / -is family).
MEDICAL_SUFFIXES = frozenset("os as us um is ys".split())

# ---------------------------------------------------------------------------
# Sound palettes. Each style defines its own phoneme inventories (weighted by
# repetition) plus a few tuning probabilities.
# ---------------------------------------------------------------------------
STYLES = {
    "plain": {
        "simple_onsets": (
            "b b b c c c d d d f f g g h h j k k l l m m m n n n "
            "p p p r r r s s s s t t t t v w w y z "
            "th th sh sh ch ch"
        ),
        "cluster_onsets": (
            "bl br cl cr dr fl fr gl gr pl pr sc sk sl sm sn sp st sw tr tw "
            "wh ph spl spr str scr thr shr"
        ),
        "nuclei": (
            "a a a a e e e e i i i i o o o o u u u "
            "ai ay ea ee ie oa oo ou au"
        ),
        "codas": (
            "b c d f g k l l m n n n p r r s s t t t x z "
            "ck ct ft ld lk lm lp lt mp nd nd ng ng nk nt nt rd rk rm rn rt "
            "sk sp st st sh th ll ss ff "
        ),
        "suffixes": (
            "a e o us um is on yn el en er ic ica ico ika ine "
            "ix yx ora ula ata ela iva os as ys ent ance ense"
        ),
        "vowel_initial_prob": 0.18,
        "cluster_prob": 0.27,
        "coda_prob": 0.30,
    },
    "heritage": {
        # Soft, flowing consonants — the romance-language / dawn palette.
        "simple_onsets": (
            "l l l r r r v v v s s m m m n n b b d d c c g t p f qu"
        ),
        # Only gentle clusters; nothing harsh or spiky.
        "cluster_onsets": "br cr dr fr gr pr tr fl cl pl bl",
        # Vowel-rich, romance-flavoured.
        "nuclei": (
            "a a a a e e e e o o o o i i i u u "
            "ia io ie ue eo ai au"
        ),
        # Mostly open syllables; only the soft romance codas.
        "codas": "l n r s l n r  ",
        # Dawn / light / romance endings — deliberately avoids -os/-as.
        "suffixes": (
            "a a o o era ero ela elo eno ena ora oro ino ina "
            "io eo al ar el en ura uro"
        ),
        "vowel_initial_prob": 0.22,
        "cluster_prob": 0.15,
        "coda_prob": 0.22,
    },
    "byzatic": {
        # Liquid, smooth consonants with a heavily weighted z.
        "simple_onsets": (
            "z z z z b b d d l l l r r r v v n n m s s t "
            "th sh"
        ),
        "cluster_onsets": "br dr tr vr zl bl gl sl",
        "nuclei": (
            "a a a e e e i i i o o y "
            "ia io ea ei y"
        ),
        "codas": "n r l s z n r l  ",
        # Smooth -atic / -ica / -yne family, echoing the sample "byzatic".
        "suffixes": (
            "atic atic atica ica ica yza yne yn iza izo elis "
            "ax yx ien eon aris"
        ),
        "vowel_initial_prob": 0.16,
        "cluster_prob": 0.18,
        "coda_prob": 0.22,
    },
}

# The four brand suffixes from the naming brief.
BRAND_SUFFIXES = ["Labs", "Works", "Solutions", "Systems"]


class Palette:
    """A resolved, tokenized sound palette for one style + flags."""

    def __init__(self, style, *, no_medical):
        spec = STYLES[style]
        self.simple_onsets = spec["simple_onsets"].split()
        self.cluster_onsets = spec["cluster_onsets"].split()
        self.nuclei = spec["nuclei"].split()
        self.digraphs = frozenset(n for n in self.nuclei if len(n) > 1)
        self.codas = spec["codas"].split() + [""] * 5  # weight open syllables
        suffixes = spec["suffixes"].split()
        if no_medical:
            suffixes = [s for s in suffixes if s not in MEDICAL_SUFFIXES]
        self.suffixes = suffixes or ["a"]
        self.vowel_initial_prob = spec["vowel_initial_prob"]
        self.cluster_prob = spec["cluster_prob"]
        self.coda_prob = spec["coda_prob"]


def _pick_nucleus(rng, pal, prev_nucleus):
    """Choose a vowel nucleus, avoiding two digraphs back to back."""
    for _ in range(5):
        nuc = rng.choice(pal.nuclei)
        if nuc in pal.digraphs and prev_nucleus in pal.digraphs:
            continue
        return nuc
    return "a"


def syllable(rng, pal, *, first, prev_had_coda, prev_nucleus):
    """Build one syllable. Cluster onsets are allowed only word-initially,
    and never right after a preceding coda, so consonant runs stay sane."""
    parts = []

    if first:
        r = rng.random()
        if r < pal.vowel_initial_prob:
            pass  # vowel-initial word
        elif r < pal.vowel_initial_prob + pal.cluster_prob and pal.cluster_onsets:
            parts.append(rng.choice(pal.cluster_onsets))
        else:
            parts.append(rng.choice(pal.simple_onsets))
    elif prev_had_coda:
        # Boundary already has a consonant; keep this onset light or empty.
        if rng.random() < 0.55:
            parts.append(rng.choice(pal.simple_onsets))
    else:
        parts.append(rng.choice(pal.simple_onsets))

    nucleus = _pick_nucleus(rng, pal, prev_nucleus)
    parts.append(nucleus)

    had_coda = False
    if rng.random() < pal.coda_prob:
        coda = rng.choice(pal.codas)
        if coda:
            parts.append(coda)
            had_coda = True

    return "".join(parts), had_coda, nucleus


def _make_one(rng, pal, min_syll, max_syll, *, suffix_prob):
    n = rng.randint(min_syll, max_syll)
    word = ""
    prev_had_coda = False
    prev_nucleus = ""
    for i in range(n):
        syl, prev_had_coda, prev_nucleus = syllable(
            rng, pal, first=(i == 0), prev_had_coda=prev_had_coda,
            prev_nucleus=prev_nucleus,
        )
        word += syl

    # Cap with a stylistic suffix, but only after a vowel so it doesn't jam
    # against a coda consonant.
    if rng.random() < suffix_prob and word and word[-1] in "aeiouy":
        word += rng.choice(pal.suffixes)

    return _tidy(word)


def make_word(rng, pal, min_syll, max_syll, *, suffix_prob, avoid_initial):
    """Generate a word, retrying if it starts with a banned initial letter."""
    for _ in range(40):
        word = _make_one(rng, pal, min_syll, max_syll, suffix_prob=suffix_prob)
        if word and word[0].lower() not in avoid_initial:
            return word
    return word  # give up after many tries rather than loop forever


def _tidy(word):
    """Collapse triple+ repeated letters to a double for pronounceability."""
    out = []
    for ch in word:
        if len(out) >= 2 and out[-1] == ch and out[-2] == ch:
            continue
        out.append(ch)
    return "".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="Generate pronounceable pseudowords that sound real but aren't."
    )
    parser.add_argument("-n", "--count", type=int, default=10,
                        help="How many words to generate (default: 10)")
    parser.add_argument("--style", choices=sorted(STYLES), default="plain",
                        help="Sound palette: plain, heritage (Spanish/Greek "
                             "dawn & light), or byzatic (smooth, z-woven). Default: plain")
    parser.add_argument("--min-syllables", type=int, default=2, metavar="N",
                        help="Minimum syllables per word (default: 2)")
    parser.add_argument("--max-syllables", type=int, default=None, metavar="N",
                        help="Maximum syllables per word (default: 3, or 2 in --brand mode)")
    parser.add_argument("--suffix-prob", type=float, default=0.25, metavar="P",
                        help="Probability [0-1] of appending a stylistic suffix (default: 0.25)")
    parser.add_argument("--avoid-initial", default="", metavar="LETTERS",
                        help="Discard words starting with any of these letters, "
                             "e.g. --avoid-initial a (case-insensitive)")
    parser.add_argument("--no-medical", action="store_true",
                        help="Drop clinical/Greek-medical endings (-os, -as, -us, -um, -is)")
    parser.add_argument("--capitalize", action="store_true",
                        help="Capitalize the first letter of each word")
    parser.add_argument("--pair-with", metavar="WORD", action="append", default=None,
                        help="Append a fixed word after each result, e.g. --pair-with Labs "
                             "(brand mode). Repeatable; one is chosen at random per word.")
    parser.add_argument("--brand", action="store_true",
                        help="Preset for company names: pairs each word with one of "
                             "Labs/Works/Solutions/Systems, capitalizes, and keeps words short")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed the RNG for reproducible output")
    args = parser.parse_args()

    # Resolve --brand preset.
    pair_with = args.pair_with
    capitalize = args.capitalize
    max_syll = args.max_syllables
    if args.brand:
        if pair_with is None:
            pair_with = list(BRAND_SUFFIXES)
        capitalize = True
        if max_syll is None:
            max_syll = 2
    if max_syll is None:
        max_syll = 3

    if args.min_syllables < 1:
        parser.error("--min-syllables must be >= 1")
    if max_syll < args.min_syllables:
        parser.error("--max-syllables must be >= --min-syllables")
    if not 0.0 <= args.suffix_prob <= 1.0:
        parser.error("--suffix-prob must be between 0 and 1")

    avoid_initial = frozenset(args.avoid_initial.lower())
    pal = Palette(args.style, no_medical=args.no_medical)
    rng = random.Random(args.seed)

    for _ in range(args.count):
        word = make_word(rng, pal, args.min_syllables, max_syll,
                         suffix_prob=args.suffix_prob, avoid_initial=avoid_initial)
        if capitalize or pair_with:
            word = word.capitalize()
        if pair_with:
            word = f"{word} {rng.choice(pair_with)}"
        print(word)


if __name__ == "__main__":
    main()

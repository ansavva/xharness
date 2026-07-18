# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Generate pronounceable pseudowords that sound real but aren't.

Words are assembled from English phonotactic building blocks — weighted
onset clusters, vowel nuclei, and coda clusters — so the output obeys the
sound patterns of real English and reads as plausible rather than random.
"""
import argparse
import random

# Single-consonant onsets — the workhorses, used anywhere in a word.
SIMPLE_ONSETS = (
    "b b b c c c d d d f f g g h h j k k l l m m m n n n "
    "p p p r r r s s s s t t t t v w w y z "
    "th th sh sh ch ch"
).split()

# Consonant-cluster onsets — richer sound, restricted to the first syllable
# so interior boundaries don't pile up unpronounceable consonant runs.
CLUSTER_ONSETS = (
    "bl br cl cr dr fl fr gl gr pl pr sc sk sl sm sn sp st sw tr tw "
    "wh ph spl spr str scr thr shr"
).split()

# Vowel nuclei — simple vowels dominate; a lighter sprinkle of digraphs.
NUCLEI = (
    "a a a a e e e e i i i i o o o o u u u "
    "ai ay ea ee ie oa oo ou au"
).split()

# Digraph nuclei we avoid placing twice in a row (keeps out vowel soup).
DIGRAPHS = frozenset("ai ay ea ee ie oa oo ou au".split())

# Coda clusters (syllable end). Empty string = open syllable (ends on vowel).
CODAS = (
    # open syllables are very common and keep words smooth/flowing
    "'' '' '' '' '' "
    # single consonants
    "b c d f g k l l m n n n p r r s s t t t x z "
    # common blends
    "ck ct ft ld lk lm lp lt mp nd nd ng ng nk nt nt rd rk rm rn rt "
    "sk sp st st sh th ll ss ff "
).replace("''", "").split() + [""] * 5

# Endings that make a word feel like a finished English/Latinate term.
SUFFIXES = (
    "a e o us um is on yn el en er ic ica ico ika ine "
    "ix yx ora ula ora ata ela iva os as ys ent ance ense"
).split()


def _pick_nucleus(rng, prev_nucleus):
    """Choose a vowel nucleus, avoiding two digraphs back to back."""
    for _ in range(5):
        nuc = rng.choice(NUCLEI)
        if nuc in DIGRAPHS and prev_nucleus in DIGRAPHS:
            continue
        return nuc
    return "a"


def syllable(rng, *, first, prev_had_coda, prev_nucleus):
    """Build one syllable. Cluster onsets are allowed only word-initially,
    and never right after a preceding coda, so consonant runs stay sane."""
    parts = []
    nucleus = None
    had_coda = False

    # Onset. First syllable may skip it (vowel-initial word) or take a
    # richer cluster; interior syllables use single consonants, and any
    # syllable following a coda takes at most a single consonant.
    if first:
        r = rng.random()
        if r < 0.18:
            pass  # vowel-initial word
        elif r < 0.45:
            parts.append(rng.choice(CLUSTER_ONSETS))
        else:
            parts.append(rng.choice(SIMPLE_ONSETS))
    elif prev_had_coda:
        # Boundary already has a consonant; keep this onset light or empty.
        if rng.random() < 0.55:
            parts.append(rng.choice(SIMPLE_ONSETS))
    else:
        parts.append(rng.choice(SIMPLE_ONSETS))

    nucleus = _pick_nucleus(rng, prev_nucleus)
    parts.append(nucleus)

    # Coda — never stack one right before the next syllable's onset if that
    # would create a run, so keep interior codas modest.
    coda_chance = 0.30
    if rng.random() < coda_chance:
        coda = rng.choice(CODAS)
        if coda:
            parts.append(coda)
            had_coda = True

    return "".join(parts), had_coda, nucleus


def make_word(rng, min_syll, max_syll, *, suffix_prob):
    n = rng.randint(min_syll, max_syll)
    word = ""
    prev_had_coda = False
    prev_nucleus = ""
    for i in range(n):
        syl, prev_had_coda, prev_nucleus = syllable(
            rng, first=(i == 0), prev_had_coda=prev_had_coda,
            prev_nucleus=prev_nucleus,
        )
        word += syl

    # Occasionally cap the word with a Latinate suffix for a coined feel —
    # but only if the word currently ends on a vowel, so we don't jam the
    # suffix against a coda consonant.
    if rng.random() < suffix_prob and word and word[-1] in "aeiou":
        word += rng.choice(SUFFIXES)

    word = _tidy(word)
    return word


def _tidy(word):
    """Clean up runs that hurt pronounceability."""
    # Collapse triple+ repeated letters to a double.
    out = []
    for ch in word:
        if len(out) >= 2 and out[-1] == ch and out[-2] == ch:
            continue
        out.append(ch)
    word = "".join(out)
    return word


def main():
    parser = argparse.ArgumentParser(
        description="Generate pronounceable pseudowords that sound real but aren't."
    )
    parser.add_argument("-n", "--count", type=int, default=10,
                        help="How many words to generate (default: 10)")
    parser.add_argument("--min-syllables", type=int, default=2, metavar="N",
                        help="Minimum syllables per word (default: 2)")
    parser.add_argument("--max-syllables", type=int, default=3, metavar="N",
                        help="Maximum syllables per word (default: 3)")
    parser.add_argument("--suffix-prob", type=float, default=0.25, metavar="P",
                        help="Probability [0-1] of appending a Latinate suffix (default: 0.25)")
    parser.add_argument("--capitalize", action="store_true",
                        help="Capitalize the first letter of each word")
    parser.add_argument("--pair-with", metavar="WORD", action="append", default=None,
                        help="Append a fixed word after each result, e.g. --pair-with Labs "
                             "(brand mode). Repeatable.")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed the RNG for reproducible output")
    args = parser.parse_args()

    if args.min_syllables < 1:
        parser.error("--min-syllables must be >= 1")
    if args.max_syllables < args.min_syllables:
        parser.error("--max-syllables must be >= --min-syllables")
    if not 0.0 <= args.suffix_prob <= 1.0:
        parser.error("--suffix-prob must be between 0 and 1")

    rng = random.Random(args.seed)

    for _ in range(args.count):
        word = make_word(rng, args.min_syllables, args.max_syllables,
                         suffix_prob=args.suffix_prob)
        if args.capitalize or args.pair_with:
            word = word.capitalize()
        if args.pair_with:
            word = f"{word} {rng.choice(args.pair_with)}"
        print(word)


if __name__ == "__main__":
    main()

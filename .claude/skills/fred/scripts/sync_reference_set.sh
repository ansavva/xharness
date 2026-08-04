#!/usr/bin/env bash
#
# sync_reference_set.sh — populate Fred's Google Drive folders. Fred's images are
# NOT stored in git; they live in Drive, and the ORIGINALS are kept SEPARATE from
# the curated REFERENCE set:
#
#   <root>/fred/originals/    all source illustrations, archived  (fred_1.webp ..)
#   <root>/fred/reference/    curated set used on every generation (fred_1.webp .. fred_9.webp)
#
# Everything uploaded is renamed to `fred_<index>.webp` (the opaque Instagram
# filenames are dropped). The reference set is a curated, re-ordered SUBSET of the
# originals — the `fred` skill downloads *this* folder and passes all of it as
# `reference_images` on every generation, so the character stays consistent
# without re-choosing references. To change the set, edit REF_MAP below.
#
# Usage:
#   .claude/skills/fred/scripts/sync_reference_set.sh [options] [SRC_DIR]
#
#   SRC_DIR            Directory holding the original .webp files. Optional; if
#                     omitted, originals are read from git history at the commit
#                     that introduced them (PR #5), so this works even after the
#                     images were removed from the working tree.
#   --reference-only  Only (re)upload the curated reference set.
#   --originals-only  Only (re)upload the originals archive.
#
# Re-runs are idempotent: drive_upload.py updates a same-named file in place
# rather than duplicating it. Requires a Google Drive credential in .env
# (see .env.example).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

DO_ORIGINALS=1
DO_REFERENCE=1
SRC_DIR=""
for arg in "$@"; do
  case "$arg" in
    --reference-only) DO_ORIGINALS=0 ;;
    --originals-only) DO_REFERENCE=0 ;;
    --*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) SRC_DIR="$arg" ;;
  esac
done

# Git ref that still contains the original images, used when SRC_DIR is absent.
# Pinned to the immutable commit that introduced them (PR #5) so the fallback
# keeps working after the images are removed from later branch tips.
ORIG_REF="${FRED_ORIG_REF:-6404638b606cc7e2685dc2057016c2d99c55e8f5}"
ORIG_PATH=".claude/skills/fred/images"

UPLOAD=".claude/skills/google-drive/scripts/drive_upload.py"

# Curated reference set: output index -> original filename. The order defines the
# [Image1]..[ImageN] slots the fred skill cites (fred_1 -> [Image1], ...).
REF_MAP=(
  "1 704636745_18083215436271388_169273655018871349_n.webp"   # face close-up (Moynihan board)
  "2 724242583_18087162908271388_6881674854106825727_n.webp"  # meditation, shirtless front — face + torso
  "3 722036716_18086433923271388_8861455302133538881_n.webp"  # full body, shirtless + jeans (field)
  "4 704851385_18083438042271388_5700159926878335343_n.webp"  # seated, white tee + leather pants (canonical)
  "5 696859676_18081809507271388_497704359430667920_n.webp"   # walking, button shirt + jeans (Warren St.)
  "6 719032765_18085959062271388_5981157241161568997_n.webp"  # porch reading, shirtless + leather — ink style
  "7 727919263_18088099868271388_8901124533000652303_n.webp"  # driving, white tank — arms + 3/4 face
  "8 731093852_18088808375271388_5012158336906692414_n.webp"  # city, white button shirt + leather (full body)
  "9 705627647_18083380835271388_7402745956609012806_n.webp"  # shaving close-up — mustache detail
)

# Materialize one original file (by its Instagram filename) to a destination path,
# from SRC_DIR, the working tree, or git history — whichever is available.
materialize() {
  local f="$1" dest="$2"
  if [ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/$f" ]; then
    cp "$SRC_DIR/$f" "$dest"
  elif [ -f "$ORIG_PATH/$f" ]; then
    cp "$ORIG_PATH/$f" "$dest"
  else
    git show "$ORIG_REF:$ORIG_PATH/$f" > "$dest"
  fi
}

# List every original filename (basename), from SRC_DIR if given else git history.
list_originals() {
  if [ -n "$SRC_DIR" ]; then
    (cd "$SRC_DIR" && ls -1 ./*.webp) | sed 's#.*/##' | sort
  else
    git ls-tree --name-only "$ORIG_REF" "$ORIG_PATH/" | sed 's#.*/##' | grep '\.webp$' | sort
  fi
}

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

if [ "$DO_ORIGINALS" = 1 ]; then
  echo "== Originals -> fred/originals ==" >&2
  mkdir -p "$STAGE/originals"
  i=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    i=$((i + 1))
    materialize "$f" "$STAGE/originals/fred_${i}.webp"
    echo "  fred_${i}.webp  <-  $f" >&2
  done < <(list_originals)
  echo "Uploading $i originals ..." >&2
  uv run "$UPLOAD" --folder fred/originals "$STAGE"/originals/*.webp
fi

if [ "$DO_REFERENCE" = 1 ]; then
  echo "== Reference set -> fred/reference ==" >&2
  mkdir -p "$STAGE/reference"
  for entry in "${REF_MAP[@]}"; do
    n="${entry%% *}"
    rest="${entry#* }"
    f="${rest%%[[:space:]]*}"   # strip trailing comment/whitespace
    materialize "$f" "$STAGE/reference/fred_${n}.webp"
    echo "  fred_${n}.webp  <-  $f" >&2
  done
  echo "Uploading ${#REF_MAP[@]} reference images ..." >&2
  uv run "$UPLOAD" --folder fred/reference "$STAGE"/reference/*.webp
fi

echo "Done. Fred's images now live in Google Drive under <root>/fred/{originals,reference}." >&2

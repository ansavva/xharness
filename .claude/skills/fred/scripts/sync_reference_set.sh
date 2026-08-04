#!/usr/bin/env bash
#
# sync_reference_set.sh — build Fred's fixed, numbered reference set and upload
# it to Google Drive (folder: <root>/fred/reference).
#
# This is a ONE-TIME migration / refresh step. Fred's reference images are NOT
# stored in git — they live in Drive. This script takes the curated originals,
# renames them to a stable numbered set (01.webp .. NN.webp), and uploads them.
# The `fred` skill then downloads this whole folder and passes every image as a
# `reference_images` input on each generation, so the character stays consistent
# without re-choosing references each time.
#
# Which images make up the set (and why) is documented in
# .claude/skills/fred/SKILL.md → "The reference set". To change the set, edit the
# MAP below and re-run.
#
# Usage:
#   .claude/skills/fred/scripts/sync_reference_set.sh [SRC_DIR]
#
#   SRC_DIR  Directory holding the original .webp files. Optional.
#            If omitted, the originals are read from git history at the commit
#            where they were introduced (PR #5), so this works even though the
#            images have been removed from the working tree.
#
# Requires a Google Drive credential in .env (see .env.example).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

SRC_DIR="${1:-}"
# Git ref that still contains the original images, used when SRC_DIR is absent.
# Pinned to the immutable commit that introduced them (PR #5) so the fallback
# keeps working after the images are removed from later branch tips.
ORIG_REF="${FRED_ORIG_REF:-6404638b606cc7e2685dc2057016c2d99c55e8f5}"
ORIG_PATH=".claude/skills/fred/images"

# number  ->  original filename   (see SKILL.md "The reference set" for rationale)
MAP=(
  "01 704636745_18083215436271388_169273655018871349_n.webp"   # face close-up (Moynihan board)
  "02 724242583_18087162908271388_6881674854106825727_n.webp"  # meditation, shirtless front — face + torso
  "03 722036716_18086433923271388_8861455302133538881_n.webp"  # full body, shirtless + jeans (field)
  "04 704851385_18083438042271388_5700159926878335343_n.webp"  # seated, white tee + leather pants (canonical)
  "05 696859676_18081809507271388_497704359430667920_n.webp"   # walking, button shirt + jeans (Warren St.)
  "06 719032765_18085959062271388_5981157241161568997_n.webp"  # porch reading, shirtless + leather — ink style
  "07 727919263_18088099868271388_8901124533000652303_n.webp"  # driving, white tank — arms + 3/4 face
  "08 731093852_18088808375271388_5012158336906692414_n.webp"  # city, white button shirt + leather (full body)
  "09 705627647_18083380835271388_7402745956609012806_n.webp"  # shaving close-up — mustache detail
)

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

echo "Building numbered reference set in $STAGE" >&2
for entry in "${MAP[@]}"; do
  n="${entry%% *}"
  f="${entry#* }"
  f="${f%%[[:space:]]*}"   # strip any trailing comment/whitespace
  if [ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/$f" ]; then
    cp "$SRC_DIR/$f" "$STAGE/$n.webp"
  elif [ -f "$ORIG_PATH/$f" ]; then
    cp "$ORIG_PATH/$f" "$STAGE/$n.webp"
  else
    echo "  $n <- $f (from git $ORIG_REF)" >&2
    git show "$ORIG_REF:$ORIG_PATH/$f" > "$STAGE/$n.webp"
  fi
done

echo "Uploading $(ls "$STAGE" | wc -l | tr -d ' ') images to Drive folder fred/reference ..." >&2
uv run .claude/skills/seedance-video/scripts/drive_upload.py --folder fred/reference "$STAGE"/*.webp
echo "Done. Fred's reference set now lives in Google Drive at <root>/fred/reference." >&2

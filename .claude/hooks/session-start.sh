#!/usr/bin/env bash
#
# SessionStart hook — runs xharness dev setup so skills are ready to use.
# Delegates to scripts/dev-setup.sh (the single source of truth for setup),
# which is idempotent and safe to run on every session start.

set -euo pipefail

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

bash "$REPO_ROOT/scripts/dev-setup.sh"

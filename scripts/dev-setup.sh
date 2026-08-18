#!/usr/bin/env bash
#
# dev-setup.sh — install the prerequisites needed to run these skills.
#
# The only hard requirement is `uv`: every skill script declares its own
# Python version and dependencies with PEP 723 inline metadata, so `uv run`
# builds and caches an isolated env per script — there is no shared venv or
# requirements.txt to install. This script installs uv (if missing) and warms
# the dependency caches for the cross-platform skills so their first real run
# is fast.
#
# Safe to run repeatedly: every step checks before it acts (idempotent) and
# runs non-interactively.

set -euo pipefail

log() { printf '\033[36m[dev-setup]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[dev-setup]\033[0m %s\n' "$*"; }

# Resolve the repo root so the script works no matter where it is invoked from.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---------------------------------------------------------------------------
# 1. Ensure uv is installed (via Homebrew) and on PATH.
# ---------------------------------------------------------------------------
# Make sure a Homebrew install is visible on PATH before we probe for uv —
# brew's bin isn't always exported yet in a bare non-interactive shell.
for brew_prefix in /opt/homebrew /usr/local /home/linuxbrew/.linuxbrew; do
  [ -x "$brew_prefix/bin/brew" ] && export PATH="$brew_prefix/bin:$PATH"
done

if command -v uv >/dev/null 2>&1; then
  log "uv already installed: $(uv --version)"
elif command -v brew >/dev/null 2>&1; then
  # Install uv via Homebrew, matching the documented setup in CLAUDE.md.
  log "installing uv via Homebrew..."
  brew install uv
  hash -r 2>/dev/null || true
  log "uv installed: $(uv --version)"
else
  warn "uv is not installed and Homebrew is unavailable."
  warn "Install Homebrew (https://brew.sh) and re-run, or install uv yourself."
  exit 1
fi

# Persist uv's directory on PATH for the rest of a Claude Code session, when
# available. Derive it from where uv actually resolves rather than assuming a
# fixed location, so it works with whatever prefix Homebrew used.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  UV_BIN_DIR="$(dirname "$(command -v uv)")"
  if ! grep -qs "$UV_BIN_DIR" "$CLAUDE_ENV_FILE" 2>/dev/null; then
    echo "export PATH=\"$UV_BIN_DIR:\$PATH\"" >> "$CLAUDE_ENV_FILE"
    log "added uv bin dir to CLAUDE_ENV_FILE"
  fi
fi

# ---------------------------------------------------------------------------
# 2. Pre-warm dependency caches for the cross-platform skills (best-effort).
#    `--help` exits 0 without doing any work, but forces uv to resolve and
#    cache each script's declared dependencies. The photos skill depends on
#    macOS-only osxphotos, so it is intentionally skipped here.
# ---------------------------------------------------------------------------
prewarm() {
  local name="$1" script="$2"
  if [ -f "$script" ]; then
    log "warming '$name' dependency cache..."
    uv run --script "$script" --help >/dev/null 2>&1 \
      || warn "could not pre-warm '$name' (will resolve on first use)"
  fi
}

prewarm qr              "$REPO_ROOT/.claude/skills/qr/scripts/generate.py"
prewarm kindle          "$REPO_ROOT/.claude/skills/kindle/scripts/kindle.py"
prewarm nytimes         "$REPO_ROOT/.claude/skills/nytimes-briefing/scripts/nytimes.py"
prewarm nytimes-search  "$REPO_ROOT/.claude/skills/nytimes-search/scripts/search.py"
prewarm drive-auth      "$REPO_ROOT/.claude/skills/google-drive/scripts/drive_auth.py"
prewarm drive-upload    "$REPO_ROOT/.claude/skills/google-drive/scripts/drive_upload.py"
prewarm drive-download  "$REPO_ROOT/.claude/skills/google-drive/scripts/drive_download.py"

# ---------------------------------------------------------------------------
# 3. Report optional external tools (never fatal — platform dependent).
#    These are only needed by specific skills and are typically installed via
#    Homebrew on macOS, per CLAUDE.md.
# ---------------------------------------------------------------------------
check_optional() {
  local bin="$1" why="$2"
  if command -v "$bin" >/dev/null 2>&1; then
    log "optional tool found: $bin"
  else
    warn "optional tool missing: $bin — $why"
  fi
}

check_optional ebook-convert "needed by the 'kindle' skill (install Calibre: https://calibre-ebook.com)"
check_optional exiftool      "needed by 'photos' metadata embedding (brew install exiftool)"
check_optional ffmpeg        "required by 'transcribe' to decode audio (brew install ffmpeg)"

log "done."

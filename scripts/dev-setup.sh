#!/usr/bin/env bash
#
# Developer / CI toolchain bootstrap for the xharness skill harness.
#
# Installs the external tools the skills shell out to, using Homebrew on BOTH
# macOS and Linux. Python itself is NOT installed here: every skill script runs
# via `uv run` with PEP 723 inline metadata, so `uv` provisions its own Python
# and per-script dependencies. This script only needs to guarantee `uv` and the
# handful of native CLIs the skills call.
#
# Tools installed:
#   - uv        core: every skill runs `uv run .../script.py`
#   - exiftool  photos skill (metadata read/embed; optional but recommended)
#   - calibre   kindle skill (`ebook-convert`); a Homebrew cask on macOS,
#               and best-effort on Linux (Homebrew has no calibre formula there)
#
# Homebrew details (mirrors how the andreas-services bootstrap handles this):
#   - macOS (developer machines): brew runs as the normal user.
#   - Linux (cloud sandbox / CI): Homebrew refuses to run as root, so it is
#     installed into the default prefix /home/linuxbrew/.linuxbrew owned by a
#     non-root user, and every `brew` call runs as that user. The prefix bin is
#     added to PATH (this run + /etc/profile.d) so root and CI agents can use it.
#
# IDEMPOTENT: every tool is checked with `command -v` before install, so
# re-running is a no-op once the toolchain is present.
#
# Usage:
#   ./scripts/dev-setup.sh            # install everything missing
#   ./scripts/dev-setup.sh --check    # report status only, install nothing
#
set -euo pipefail

CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

log()  { printf '\033[1;34m[dev-setup]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[ ok ]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
skip() { printf '\033[1;36m[skip]\033[0m %s already present: %s\n' "$1" "$2"; }

# Detect platform from the kernel name. `uname -s` is the kernel identifier: it
# is reliably "Darwin" on every macOS release (it does NOT track the macOS
# marketing version) and "Linux" on Linux. Match with a glob and treat anything
# else as unsupported rather than silently assuming Linux.
OS="$(uname -s)"
case "$OS" in
  Darwin*) PLATFORM="macos" ;;
  Linux*)  PLATFORM="linux" ;;
  *) printf 'Unsupported OS: %s (this repo supports macOS and Linux only).\n' "$OS" >&2; exit 1 ;;
esac
have() { command -v "$1" >/dev/null 2>&1; }
if [[ "$(id -u)" -eq 0 ]]; then SUDO=""; else SUDO="sudo"; fi

# --- Linux Homebrew (installed & run as a non-root user) -------------------
LINUXBREW_PREFIX="/home/linuxbrew/.linuxbrew"
BREW_ENV=(HOMEBREW_NO_ANALYTICS=1 HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_ENV_HINTS=1)

# Resolve the non-root user Homebrew runs as on Linux. Prefer $BREW_USER, then a
# conventional `ubuntu` account, then the invoking sudo user, then ourselves.
LINUX_BREW_USER="${BREW_USER:-}"
if [[ -z "$LINUX_BREW_USER" ]]; then
  if id ubuntu >/dev/null 2>&1;         then LINUX_BREW_USER="ubuntu"
  elif [[ -n "${SUDO_USER:-}" ]];       then LINUX_BREW_USER="$SUDO_USER"
  else                                       LINUX_BREW_USER="$(id -un)"; fi
fi

# Run a brew command the right way for the platform. On Linux, run brew directly
# when we already are the brew user, otherwise drop privileges to that user.
brew_run() {
  if [[ "$PLATFORM" == "macos" ]]; then
    env "${BREW_ENV[@]}" brew "$@"
  elif [[ "$(id -un)" == "$LINUX_BREW_USER" ]]; then
    env "${BREW_ENV[@]}" "$LINUXBREW_PREFIX/bin/brew" "$@"
  else
    $SUDO -u "$LINUX_BREW_USER" env "${BREW_ENV[@]}" "$LINUXBREW_PREFIX/bin/brew" "$@"
  fi
}

apt_install() { $SUDO apt-get update -y >/dev/null && $SUDO apt-get install -y "$@"; }

ensure_brew() {
  if [[ "$PLATFORM" == "macos" ]]; then
    if have brew; then return 0; fi
    if [[ "$CHECK_ONLY" -eq 1 ]]; then warn "Homebrew is MISSING (required on macOS)"; return 1; fi
    log "installing Homebrew ..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    return 0
  fi

  # ---- Linux ----
  if [[ ! -x "$LINUXBREW_PREFIX/bin/brew" ]]; then
    if [[ "$CHECK_ONLY" -eq 1 ]]; then warn "Homebrew (Linux) is MISSING (would install as user '$LINUX_BREW_USER')"; return 1; fi
    if [[ "$(id -u)" -eq 0 ]] && ! id "$LINUX_BREW_USER" >/dev/null 2>&1; then
      warn "running as root and non-root user '$LINUX_BREW_USER' not found; Homebrew cannot run as root."
      warn "set BREW_USER=<name> to a non-root account and re-run."
      return 1
    fi
    log "installing Homebrew prerequisites ..."
    apt_install build-essential procps curl file git >/dev/null 2>&1 || \
      warn "could not apt-get prerequisites (continuing; they may already be present)"
    log "installing Homebrew into $LINUXBREW_PREFIX (owned by $LINUX_BREW_USER) ..."
    $SUDO mkdir -p "$LINUXBREW_PREFIX"
    $SUDO chown -R "$LINUX_BREW_USER:$LINUX_BREW_USER" "$(dirname "$LINUXBREW_PREFIX")"
    $SUDO -u "$LINUX_BREW_USER" git clone --depth=1 https://github.com/Homebrew/brew "$LINUXBREW_PREFIX/Homebrew"
    $SUDO -u "$LINUX_BREW_USER" mkdir -p "$LINUXBREW_PREFIX/bin"
    $SUDO -u "$LINUX_BREW_USER" ln -sf "$LINUXBREW_PREFIX/Homebrew/bin/brew" "$LINUXBREW_PREFIX/bin/brew"
  fi

  # Expose brew + its tools on PATH for this run and for future login shells.
  eval "$("$LINUXBREW_PREFIX/bin/brew" shellenv)"
  local profile="/etc/profile.d/homebrew.sh"
  if [[ "$CHECK_ONLY" -ne 1 && ! -f "$profile" ]]; then
    echo "eval \"\$($LINUXBREW_PREFIX/bin/brew shellenv)\"" | $SUDO tee "$profile" >/dev/null || true
  fi
  return 0
}

# brew_ensure <cli-name> <formula>
brew_ensure() {
  local cli="$1" formula="$2"
  if have "$cli"; then skip "$cli" "$(command -v "$cli")"; return 0; fi
  if [[ "$CHECK_ONLY" -eq 1 ]]; then warn "$cli is MISSING (would: brew install $formula)"; return 0; fi
  log "installing $formula ..."
  brew_run install "$formula"
}

# Calibre provides `ebook-convert` for the kindle skill. It is a Homebrew *cask*
# on macOS; Homebrew has no calibre formula on Linux, so fall back to apt there.
# (Kindle Previewer 3 — the final kindle step — is macOS/Windows only and is not
# scriptable via Homebrew; the skill's own pre-flight handles that.)
ensure_calibre() {
  if have ebook-convert; then skip ebook-convert "$(command -v ebook-convert)"; return 0; fi
  if [[ "$CHECK_ONLY" -eq 1 ]]; then
    warn "ebook-convert is MISSING (kindle skill; would install Calibre)"
    return 0
  fi
  if [[ "$PLATFORM" == "macos" ]]; then
    log "installing Calibre (cask) ..."
    brew_run install --cask calibre
  else
    log "installing Calibre via apt (Homebrew has no Linux calibre formula) ..."
    if apt_install calibre >/dev/null 2>&1; then
      ok "calibre installed via apt"
    else
      warn "could not install Calibre automatically."
      warn "install it from https://calibre-ebook.com and ensure 'ebook-convert' is on PATH."
    fi
  fi
}

# ---------------------------------------------------------------------------
log "OS detected: $OS  (check-only: $CHECK_ONLY)"

if ! ensure_brew; then
  warn "Homebrew is not available; cannot continue. See messages above."
  exit 1
fi

brew_ensure uv       uv
brew_ensure exiftool exiftool
ensure_calibre

# Kindle Previewer 3 is a manual, macOS/Windows-only GUI download — check only.
if [[ "$PLATFORM" == "macos" ]]; then
  if [[ -d "/Applications/Kindle Previewer 3.app" ]]; then
    ok "Kindle Previewer 3 present"
  else
    warn "Kindle Previewer 3 not found (optional; final kindle step) — https://www.amazon.com/Kindle-Previewer/b?node=21381691011"
  fi
fi

log "toolchain ready. Skills run their Python via 'uv run', e.g.:"
log "    uv run .claude/skills/wordgen/scripts/wordgen.py --style heritage --brand"
[[ "$PLATFORM" == "linux" && "$CHECK_ONLY" -ne 1 ]] && log "Tools are on PATH via /etc/profile.d/homebrew.sh (new shells) or: eval \"\$($LINUXBREW_PREFIX/bin/brew shellenv)\""
ok "done."

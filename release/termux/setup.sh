#!/data/data/com.termux/files/usr/bin/bash
# ARGO Agent v3.0 — Termux (Android) setup script.  BETA / brain-only.
#
# Termux is a terminal-emulator app that provides a Linux-like userland on
# Android. ARGO's Python brain (argo-brain) is standard-library-only, so it
# runs on Termux directly with no third-party packages.
#
# The Rust gateway (argo-core) is OPTIONAL and is NOT built by this script:
# cross-compiling Rust on a phone is heavy and rarely worthwhile. ARGO
# therefore runs on Termux in "brain-only" mode — the stdlib brain serves
# the agent loop, tools, memory and channels by itself, including its own
# HTTP gateway via `argo_brain serve`.
#
# This script:
#   1. updates the Termux package index and installs `python`;
#   2. prepares the ~/.argo directory layout;
#   3. installs the argo_brain package and an `argo` launcher on PATH;
#   4. runs the brain's diagnostics and prints next steps.
#
# It is idempotent — safe to re-run.
#
# Usage (from inside the ARGO repository checkout):
#   bash release/termux/setup.sh
#
# Environment overrides:
#   ARGO_HOME   data / config dir   (default: ~/.argo)

set -euo pipefail

# --- 0. resolve paths --------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ARGO_HOME="${ARGO_HOME:-${HOME}/.argo}"

# Termux's per-user prefix; PREFIX is normally exported by Termux itself.
TERMUX_PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
BIN_DIR="${TERMUX_PREFIX}/bin"
LIB_DIR="${ARGO_HOME}/lib"

# --- helpers -----------------------------------------------------------------
info() { printf '       %s\n' "$*"; }
ok()   { printf '  OK   %s\n' "$*"; }
warn() { printf '  WARN %s\n' "$*"; }
die()  { printf '  ERR  %s\n' "$*" >&2; exit 1; }

echo "=============================================="
echo "  ARGO Agent v3.0 - Termux setup (BETA)"
echo "=============================================="
echo "Repo:      ${REPO_ROOT}"
echo "ARGO_HOME: ${ARGO_HOME}"
echo "Mode:      brain-only (argo-core not built on Termux)"
echo

# --- 1. sanity-check that we are on Termux -----------------------------------
if [ ! -d "${TERMUX_PREFIX}" ]; then
    die "Termux prefix ${TERMUX_PREFIX} not found - run this inside the Termux app."
fi

# --- 2. install Python via pkg ----------------------------------------------
# `pkg` is Termux's package manager (a wrapper around apt).
if ! command -v pkg >/dev/null 2>&1; then
    die "the 'pkg' command was not found - this does not look like Termux."
fi

echo "Updating the Termux package index..."
# `pkg update` refreshes the index; -y answers any prompts.
pkg update -y
ok "package index updated"

if command -v python3 >/dev/null 2>&1; then
    PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    ok "python already installed (python3 ${PY_VER})"
else
    echo "Installing python..."
    pkg install -y python
    ok "python installed"
fi

# argo-brain needs Python 3.11+ (3.12 recommended). Termux ships a current
# Python, but verify rather than assume.
PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)'; then
    ok "python3 ${PY_VER} (>= 3.11)"
else
    die "Python 3.11+ required, found ${PY_VER} - run 'pkg upgrade python'"
fi

# --- 3. ARGO_HOME directory layout ------------------------------------------
echo
info "Preparing ${ARGO_HOME}..."
mkdir -p "${ARGO_HOME}/data" "${ARGO_HOME}/skills" "${ARGO_HOME}/plugins" "${LIB_DIR}"
ok "${ARGO_HOME}/{data,skills,plugins,lib}"

# --- 4. install the argo-brain package --------------------------------------
# The brain is stdlib-only, so "installing" it is just a file copy.
echo
info "Installing the argo-brain Python package..."
BRAIN_SRC="${REPO_ROOT}/argo-brain/argo_brain"
[ -d "${BRAIN_SRC}" ] || die "argo-brain/argo_brain not found under ${REPO_ROOT}"
# Remove any previous copy so re-runs are a clean refresh.
rm -rf "${LIB_DIR}/argo_brain"
cp -r "${BRAIN_SRC}" "${LIB_DIR}/argo_brain"
# Drop stale bytecode caches that may have come along in the copy.
find "${LIB_DIR}/argo_brain" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
ok "${LIB_DIR}/argo_brain"

# --- 5. install the `argo` launcher -----------------------------------------
# A small wrapper on PATH so `argo <command>` works from any directory.
# Brain-only: there is no `argo core` subcommand on Termux.
echo
info "Installing the argo launcher..."
cat > "${BIN_DIR}/argo" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
# ARGO Agent launcher (installed by release/termux/setup.sh).
# Termux runs ARGO in brain-only mode - every command goes to the brain.
set -euo pipefail
export ARGO_HOME="${ARGO_HOME}"
export PYTHONPATH="${LIB_DIR}\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m argo_brain "\$@"
EOF
chmod 0755 "${BIN_DIR}/argo"
ok "${BIN_DIR}/argo"

# --- 6. diagnostics ----------------------------------------------------------
echo
info "Running diagnostics..."
ARGO_HOME="${ARGO_HOME}" PYTHONPATH="${LIB_DIR}" python3 -m argo_brain doctor || \
    warn "doctor reported issues - review the output above"

# --- 7. summary --------------------------------------------------------------
echo
echo "=============================================="
echo "  Termux setup complete (brain-only mode)."
echo "=============================================="
echo
echo "Installed:"
echo "  ${BIN_DIR}/argo        - launcher"
echo "  ${LIB_DIR}/argo_brain  - Python brain"
echo
echo "Next steps:"
echo "  argo setup     # interactive setup wizard"
echo "  argo chat      # interactive conversation (no API key needed)"
echo "  argo serve     # HTTP gateway on http://127.0.0.1:8000"
echo
echo "argo-core (the Rust gateway) is NOT installed on Termux. The brain"
echo "runs standalone - see release/termux/README.md for details."

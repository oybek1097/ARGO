#!/usr/bin/env bash
# ARGO Agent v3.0 — one-shot setup / installer (spec section 7.4).
#
# Detects the toolchain, builds argo-core if Rust is available, prepares the
# ~/.argo directory layout, then hands off to the interactive `argo setup`
# wizard. Safe to re-run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARGO_HOME="${ARGO_HOME:-$HOME/.argo}"

echo "=============================================="
echo "  ARGO Agent v3.0 — setup"
echo "=============================================="
echo "Repo:      $REPO_ROOT"
echo "ARGO_HOME: $ARGO_HOME"
echo

# --- 1. dependency checks ----------------------------------------------------
fail=0

if command -v python3 >/dev/null 2>&1; then
    PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    echo "  OK    python3 $PY_VER"
    python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' \
        || { echo "  XATO  Python 3.11+ kerak"; fail=1; }
else
    echo "  XATO  python3 topilmadi"
    fail=1
fi

HAVE_CARGO=0
if command -v cargo >/dev/null 2>&1; then
    echo "  OK    cargo $(cargo --version | awk '{print $2}')"
    HAVE_CARGO=1
else
    echo "  SKIP  cargo topilmadi — argo-core qurilmaydi (brain mustaqil ishlaydi)"
fi

[ "$fail" -eq 0 ] || { echo; echo "Sozlash to'xtatildi: majburiy bog'liqlik yetishmayapti."; exit 1; }

# --- 2. directory layout -----------------------------------------------------
echo
echo "Kataloglar tayyorlanmoqda..."
mkdir -p "$ARGO_HOME/data" "$ARGO_HOME/skills" "$ARGO_HOME/plugins"
echo "  OK    $ARGO_HOME/{data,skills,plugins}"

# --- 3. build argo-core ------------------------------------------------------
if [ "$HAVE_CARGO" -eq 1 ] && [ -f "$REPO_ROOT/argo-core/Cargo.toml" ]; then
    echo
    echo "argo-core (Rust gateway) qurilmoqda — bu biroz vaqt oladi..."
    ( cd "$REPO_ROOT/argo-core" && cargo build --release --quiet )
    echo "  OK    $REPO_ROOT/argo-core/target/release/argo-core"
fi

# --- 4. interactive wizard ---------------------------------------------------
echo
echo "Sozlash sehrgari ishga tushirilmoqda..."
echo
( cd "$REPO_ROOT/argo-brain" && python3 -m argo_brain setup )

echo
echo "=============================================="
echo "  Sozlash tugadi."
echo "=============================================="

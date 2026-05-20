#!/usr/bin/env bash
# ARGO Agent v3.0 — native installer (no Docker).
#
# Installs ARGO directly onto the host:
#   1. detects the OS (Linux or macOS) and CPU architecture;
#   2. checks for the required toolchain (Python 3.12+, cargo);
#   3. builds argo-core (the Rust gateway) with cargo;
#   4. installs argo-core and the stdlib-only argo-brain package under a
#      prefix, plus an `argo` launcher on the PATH;
#   5. sets up the ~/.argo directory layout;
#   6. registers a background service — a systemd unit on Linux, a launchd
#      plist on macOS — for the argo-core gateway.
#
# ARGO is alpha approaching its v3.0.0 GA: this script is intentionally
# simple and readable. Re-running it is safe (it overwrites the installed
# files and refreshes the service definition).
#
# Usage:
#   ./scripts/install.sh                 # install for the current user
#   PREFIX=/usr/local sudo ./scripts/install.sh   # system-wide install
#
# Environment overrides:
#   PREFIX        install prefix       (default: ~/.local)
#   ARGO_HOME     data / config dir    (default: ~/.argo)
#   ARGO_CORE_HOST / ARGO_CORE_PORT    gateway bind address (default 127.0.0.1:8000)
#   NO_SERVICE=1  skip service registration

set -euo pipefail

# --- 0. resolve paths --------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PREFIX="${PREFIX:-${HOME}/.local}"
ARGO_HOME="${ARGO_HOME:-${HOME}/.argo}"
ARGO_CORE_HOST="${ARGO_CORE_HOST:-127.0.0.1}"
ARGO_CORE_PORT="${ARGO_CORE_PORT:-8000}"
NO_SERVICE="${NO_SERVICE:-0}"

# Where files land.
BIN_DIR="${PREFIX}/bin"
LIB_DIR="${PREFIX}/lib/argo-agent"

# --- helpers -----------------------------------------------------------------
info()  { printf '  %s\n' "$*"; }
ok()    { printf '  OK    %s\n' "$*"; }
warn()  { printf '  WARN  %s\n' "$*"; }
die()   { printf '  ERROR %s\n' "$*" >&2; exit 1; }

echo "=============================================="
echo "  ARGO Agent v3.0 — native installer"
echo "=============================================="
echo "Repo:      ${REPO_ROOT}"
echo "Prefix:    ${PREFIX}"
echo "ARGO_HOME: ${ARGO_HOME}"
echo

# --- 1. detect the operating system -----------------------------------------
UNAME_S="$(uname -s)"
case "${UNAME_S}" in
    Linux)  OS="linux"  ;;
    Darwin) OS="macos"  ;;
    *)      die "unsupported operating system: ${UNAME_S} (Linux or macOS required)" ;;
esac
ok "operating system: ${OS} ($(uname -m))"

# --- 2. toolchain checks -----------------------------------------------------
# Python 3.12+ is required for argo-brain.
if ! command -v python3 >/dev/null 2>&1; then
    die "python3 not found — install Python 3.12 or newer"
fi
PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)'; then
    ok "python3 ${PY_VER}"
else
    die "Python 3.12+ required, found ${PY_VER}"
fi

# cargo is required to build argo-core.
if ! command -v cargo >/dev/null 2>&1; then
    die "cargo not found — install the Rust toolchain from https://rustup.rs"
fi
ok "cargo $(cargo --version | awk '{print $2}')"

# --- 3. build argo-core ------------------------------------------------------
[ -f "${REPO_ROOT}/argo-core/Cargo.toml" ] \
    || die "argo-core/Cargo.toml not found — run this script from an ARGO checkout"

echo
info "Building argo-core (Rust gateway) — this may take a few minutes..."
( cd "${REPO_ROOT}/argo-core" && cargo build --release )
CORE_BIN="${REPO_ROOT}/argo-core/target/release/argo-core"
[ -x "${CORE_BIN}" ] || die "build finished but ${CORE_BIN} is missing"
ok "built ${CORE_BIN}"

# --- 4. install the files ----------------------------------------------------
echo
info "Installing files..."
mkdir -p "${BIN_DIR}" "${LIB_DIR}"

# argo-core binary.
install -m 0755 "${CORE_BIN}" "${BIN_DIR}/argo-core"
ok "${BIN_DIR}/argo-core"

# argo-brain Python package (stdlib-only — no pip install needed).
rm -rf "${LIB_DIR}/argo_brain"
cp -r "${REPO_ROOT}/argo-brain/argo_brain" "${LIB_DIR}/argo_brain"
ok "${LIB_DIR}/argo_brain"

# `argo` launcher: `argo core ...` runs the gateway, everything else is
# forwarded to `python3 -m argo_brain`.
cat > "${BIN_DIR}/argo" <<EOF
#!/usr/bin/env bash
# ARGO Agent launcher (installed by scripts/install.sh).
set -euo pipefail
if [ "\${1:-}" = "core" ]; then
    shift
    exec "${BIN_DIR}/argo-core" "\$@"
fi
export PYTHONPATH="${LIB_DIR}\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m argo_brain "\$@"
EOF
chmod 0755 "${BIN_DIR}/argo"
ok "${BIN_DIR}/argo"

# --- 5. ARGO_HOME directory layout -------------------------------------------
echo
info "Preparing ${ARGO_HOME}..."
mkdir -p "${ARGO_HOME}/data" "${ARGO_HOME}/skills" "${ARGO_HOME}/plugins"
ok "${ARGO_HOME}/{data,skills,plugins}"

# --- 6. register the background service -------------------------------------
if [ "${NO_SERVICE}" = "1" ]; then
    echo
    warn "NO_SERVICE=1 set — skipping service registration"
elif [ "${OS}" = "linux" ]; then
    echo
    info "Registering the systemd service for argo-core..."
    if ! command -v systemctl >/dev/null 2>&1 || [ ! -d /run/systemd/system ]; then
        warn "systemd not detected — skipping. Start the gateway manually:"
        warn "  ARGO_HOME=${ARGO_HOME} ${BIN_DIR}/argo-core"
    else
        # A user service avoids needing root; it runs as the current user.
        UNIT_DIR="${HOME}/.config/systemd/user"
        mkdir -p "${UNIT_DIR}"
        cat > "${UNIT_DIR}/argo-agent.service" <<EOF
[Unit]
Description=ARGO Agent — Rust gateway (argo-core)
Documentation=https://github.com/argo-agent/argo
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=ARGO_HOME=${ARGO_HOME}
Environment=ARGO_CORE_HOST=${ARGO_CORE_HOST}
Environment=ARGO_CORE_PORT=${ARGO_CORE_PORT}
ExecStart=${BIN_DIR}/argo-core
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF
        systemctl --user daemon-reload
        systemctl --user enable --now argo-agent.service
        ok "systemd user service 'argo-agent' enabled and started"
        info "Manage it with: systemctl --user {status,restart,stop} argo-agent"
        info "Tip: run 'loginctl enable-linger ${USER}' to keep it running after logout."
    fi
elif [ "${OS}" = "macos" ]; then
    echo
    info "Registering the launchd service for argo-core..."
    PLIST_DIR="${HOME}/Library/LaunchAgents"
    PLIST="${PLIST_DIR}/dev.argo-agent.core.plist"
    mkdir -p "${PLIST_DIR}"
    cat > "${PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>dev.argo-agent.core</string>
    <key>ProgramArguments</key>
    <array>
        <string>${BIN_DIR}/argo-core</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ARGO_HOME</key>
        <string>${ARGO_HOME}</string>
        <key>ARGO_CORE_HOST</key>
        <string>${ARGO_CORE_HOST}</string>
        <key>ARGO_CORE_PORT</key>
        <string>${ARGO_CORE_PORT}</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${ARGO_HOME}/argo-core.log</string>
    <key>StandardErrorPath</key>
    <string>${ARGO_HOME}/argo-core.log</string>
</dict>
</plist>
EOF
    # Reload: unload an existing instance first so re-runs are idempotent.
    launchctl unload "${PLIST}" 2>/dev/null || true
    launchctl load "${PLIST}"
    ok "launchd agent 'dev.argo-agent.core' loaded"
    info "Manage it with: launchctl {unload,load} ${PLIST}"
fi

# --- 7. summary --------------------------------------------------------------
echo
echo "=============================================="
echo "  Installation complete."
echo "=============================================="
echo
echo "Installed:"
echo "  ${BIN_DIR}/argo        — launcher"
echo "  ${BIN_DIR}/argo-core   — Rust gateway"
echo "  ${LIB_DIR}/argo_brain  — Python brain"
echo
if ! command -v argo >/dev/null 2>&1; then
    echo "NOTE: ${BIN_DIR} is not on your PATH. Add it, e.g.:"
    echo "  export PATH=\"${BIN_DIR}:\$PATH\""
    echo
fi
echo "Next steps:"
echo "  argo setup          # interactive setup wizard"
echo "  argo doctor         # diagnostics"
echo "  argo chat           # interactive conversation (no API key needed)"
echo
echo "The argo-core gateway listens on http://${ARGO_CORE_HOST}:${ARGO_CORE_PORT}"
echo "  curl http://${ARGO_CORE_HOST}:${ARGO_CORE_PORT}/api/health"

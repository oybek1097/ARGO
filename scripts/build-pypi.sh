#!/usr/bin/env bash
# build-pypi.sh — build the `argo-brain` sdist + wheel and validate them.
#
# Produces distributions under argo-brain/dist/ and runs `twine check`.
# See release/pypi/RELEASING.md for the full release runbook.
set -euo pipefail

# Resolve the repo root from this script's location, regardless of CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BRAIN_DIR="${REPO_ROOT}/argo-brain"
DIST_DIR="${BRAIN_DIR}/dist"

PYTHON="${PYTHON:-python3}"

echo "==> ARGO argo-brain — PyPI build"
echo "    repo root : ${REPO_ROOT}"
echo "    package   : ${BRAIN_DIR}"
echo

if [[ ! -f "${BRAIN_DIR}/pyproject.toml" ]]; then
    echo "error: ${BRAIN_DIR}/pyproject.toml not found" >&2
    exit 1
fi

# Ensure the build toolchain is available.
echo "==> Checking build toolchain"
if ! "${PYTHON}" -c "import build" >/dev/null 2>&1; then
    echo "error: the 'build' package is missing. Install it with:" >&2
    echo "       ${PYTHON} -m pip install --upgrade build twine" >&2
    exit 1
fi
if ! "${PYTHON}" -c "import twine" >/dev/null 2>&1; then
    echo "error: the 'twine' package is missing. Install it with:" >&2
    echo "       ${PYTHON} -m pip install --upgrade build twine" >&2
    exit 1
fi

# Clean previous artifacts.
echo "==> Cleaning previous build artifacts"
rm -rf "${DIST_DIR}" "${BRAIN_DIR}/build"
find "${BRAIN_DIR}" -maxdepth 1 -name "*.egg-info" -exec rm -rf {} +

# Build sdist + wheel.
echo "==> Building sdist and wheel"
"${PYTHON}" -m build --sdist --wheel --outdir "${DIST_DIR}" "${BRAIN_DIR}"

# Validate metadata.
echo "==> Running twine check"
"${PYTHON}" -m twine check "${DIST_DIR}"/*

echo
echo "==> Build complete. Artifacts in ${DIST_DIR}:"
ls -1 "${DIST_DIR}"
echo
echo "Next steps:"
echo "  1. Smoke-test the wheel in a clean virtualenv (see RELEASING.md)."
echo "  2. TestPyPI dry-run:  twine upload --repository testpypi ${DIST_DIR}/*"
echo "  3. Tag the release:   git tag -a v3.0.0 -m 'ARGO Agent v3.0.0 GA' && git push origin v3.0.0"
echo "  4. The 'v*' tag triggers .github/workflows/release-pypi.yml to publish via OIDC."

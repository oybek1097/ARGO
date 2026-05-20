#!/usr/bin/env bash
#
# security-audit.sh — ARGO Agent security self-audit.
#
# Runs the security scanners listed in the technical specification
# (section 11): bandit, semgrep, cargo-audit and trivy. Each scanner is
# optional: if a tool is not installed the script reports it as SKIPPED
# and continues. The script only fails if a scanner that *did* run
# reported findings, or on an unexpected error.
#
# Usage:
#   scripts/security-audit.sh [--strict]
#
#   --strict   Treat SKIPPED (missing) scanners as a failure. Intended
#              for CI where every scanner is expected to be present.
#
set -euo pipefail

# --- locate the repository root ---------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BRAIN_DIR="${REPO_ROOT}/argo-brain"
CORE_DIR="${REPO_ROOT}/argo-core"

STRICT=0
if [[ "${1:-}" == "--strict" ]]; then
  STRICT=1
fi

# --- result tracking ---------------------------------------------------
declare -a SUMMARY=()
RUN_COUNT=0
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Colours, only when stdout is a terminal.
if [[ -t 1 ]]; then
  C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YEL=$'\033[33m'
  C_BLU=$'\033[34m'; C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_RST=""
fi

log()  { printf '%s\n' "$*"; }
hdr()  { printf '\n%s== %s ==%s\n' "${C_BLU}" "$*" "${C_RST}"; }

record() {
  # record <name> <PASS|FAIL|SKIP> <message>
  local name="$1" status="$2" msg="$3"
  case "${status}" in
    PASS) PASS_COUNT=$((PASS_COUNT + 1)); RUN_COUNT=$((RUN_COUNT + 1))
          SUMMARY+=("${C_GRN}PASS${C_RST}  ${name} — ${msg}") ;;
    FAIL) FAIL_COUNT=$((FAIL_COUNT + 1)); RUN_COUNT=$((RUN_COUNT + 1))
          SUMMARY+=("${C_RED}FAIL${C_RST}  ${name} — ${msg}") ;;
    SKIP) SKIP_COUNT=$((SKIP_COUNT + 1))
          SUMMARY+=("${C_YEL}SKIP${C_RST}  ${name} — ${msg}") ;;
  esac
}

have() { command -v "$1" >/dev/null 2>&1; }

# --- scanner: bandit (Python SAST) ------------------------------------
run_bandit() {
  hdr "bandit (Python SAST)"
  if ! have bandit; then
    log "${C_YEL}bandit not installed — skipping.${C_RST}"
    log "  install: pip install bandit"
    record "bandit" SKIP "not installed"
    return 0
  fi
  if [[ ! -d "${BRAIN_DIR}/argo_brain" ]]; then
    log "${C_YEL}argo-brain source not found — skipping.${C_RST}"
    record "bandit" SKIP "argo-brain source not found"
    return 0
  fi
  local rc=0
  bandit -r "${BRAIN_DIR}/argo_brain" -ll -q || rc=$?
  if [[ ${rc} -eq 0 ]]; then
    record "bandit" PASS "no medium+ findings"
  else
    record "bandit" FAIL "findings reported (exit ${rc})"
  fi
  return 0
}

# --- scanner: semgrep (multi-language SAST) ---------------------------
run_semgrep() {
  hdr "semgrep (SAST)"
  if ! have semgrep; then
    log "${C_YEL}semgrep not installed — skipping.${C_RST}"
    log "  install: pip install semgrep"
    record "semgrep" SKIP "not installed"
    return 0
  fi
  local rc=0
  semgrep --config=auto --error --quiet "${REPO_ROOT}" || rc=$?
  if [[ ${rc} -eq 0 ]]; then
    record "semgrep" PASS "no findings"
  else
    record "semgrep" FAIL "findings reported (exit ${rc})"
  fi
  return 0
}

# --- scanner: cargo-audit (Rust dependency CVEs) ----------------------
run_cargo_audit() {
  hdr "cargo-audit (Rust dependencies)"
  if ! have cargo; then
    log "${C_YEL}cargo not installed — skipping.${C_RST}"
    record "cargo-audit" SKIP "cargo not installed"
    return 0
  fi
  if ! cargo audit --version >/dev/null 2>&1; then
    log "${C_YEL}cargo-audit not installed — skipping.${C_RST}"
    log "  install: cargo install cargo-audit"
    record "cargo-audit" SKIP "cargo-audit not installed"
    return 0
  fi
  if [[ ! -f "${CORE_DIR}/Cargo.lock" ]]; then
    log "${C_YEL}argo-core/Cargo.lock not found — skipping.${C_RST}"
    record "cargo-audit" SKIP "Cargo.lock not found"
    return 0
  fi
  local rc=0
  ( cd "${CORE_DIR}" && cargo audit ) || rc=$?
  if [[ ${rc} -eq 0 ]]; then
    record "cargo-audit" PASS "no known vulnerable crates"
  else
    record "cargo-audit" FAIL "vulnerable crates reported (exit ${rc})"
  fi
  return 0
}

# --- scanner: trivy (filesystem / image CVEs) -------------------------
run_trivy() {
  hdr "trivy (filesystem scan)"
  if ! have trivy; then
    log "${C_YEL}trivy not installed — skipping.${C_RST}"
    log "  install: https://aquasecurity.github.io/trivy/"
    record "trivy" SKIP "not installed"
    return 0
  fi
  local rc=0
  trivy fs --quiet --scanners vuln,secret,misconfig \
        --severity HIGH,CRITICAL --exit-code 1 "${REPO_ROOT}" || rc=$?
  if [[ ${rc} -eq 0 ]]; then
    record "trivy" PASS "no HIGH/CRITICAL findings"
  else
    record "trivy" FAIL "HIGH/CRITICAL findings reported (exit ${rc})"
  fi
  return 0
}

# --- main --------------------------------------------------------------
log "${C_BLU}ARGO Agent — security self-audit${C_RST}"
log "repository: ${REPO_ROOT}"
[[ ${STRICT} -eq 1 ]] && log "mode: strict (missing scanners fail the run)"

run_bandit
run_semgrep
run_cargo_audit
run_trivy

# --- summary -----------------------------------------------------------
hdr "Summary"
for line in "${SUMMARY[@]}"; do
  printf '  %s\n' "${line}"
done
log ""
log "scanners run: ${RUN_COUNT}  passed: ${PASS_COUNT}  failed: ${FAIL_COUNT}  skipped: ${SKIP_COUNT}"

EXIT=0
if [[ ${FAIL_COUNT} -gt 0 ]]; then
  log "${C_RED}Security audit FAILED: ${FAIL_COUNT} scanner(s) reported findings.${C_RST}"
  EXIT=1
elif [[ ${STRICT} -eq 1 && ${SKIP_COUNT} -gt 0 ]]; then
  log "${C_RED}Security audit FAILED (strict): ${SKIP_COUNT} scanner(s) missing.${C_RST}"
  EXIT=1
elif [[ ${RUN_COUNT} -eq 0 ]]; then
  log "${C_YEL}No scanners were available to run. Install bandit, semgrep,${C_RST}"
  log "${C_YEL}cargo-audit and/or trivy for a meaningful audit.${C_RST}"
  # Not a failure in non-strict mode: nothing was actually checked.
else
  log "${C_GRN}Security audit PASSED.${C_RST}"
fi

exit ${EXIT}

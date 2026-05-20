#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# ARGO Agent v3.0 — Google Compute Engine startup script.
#
# Attach this to a VM as the `startup-script` metadata key (the gcloud
# command in this directory's README does exactly that). GCE runs it on
# every boot; the steps are idempotent so a reboot just re-checks state.
#
# Steps (identical to deploy/cloud/cloud-init.yaml):
#   1. Install Docker Engine and the Docker Compose plugin.
#   2. Clone the ARGO repository into /opt/argo/ARGO.
#   3. Run `docker compose up -d --build`.
#
# Output is captured by the GCE serial console and /var/log/syslog.
# ---------------------------------------------------------------------------
set -euo pipefail

# Repository to deploy. Override the ref via the `argo-repo-ref` instance
# metadata key if you want a specific tag instead of `main`.
ARGO_REPO_URL="https://github.com/argo-agent/argo.git"
ARGO_REPO_REF="$(curl -fsS -H 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/instance/attributes/argo-repo-ref' \
  2>/dev/null || echo main)"
ARGO_DIR="/opt/argo/ARGO"

echo "[argo] Installing base packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git

echo "[argo] Installing Docker Engine..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

echo "[argo] Fetching the ARGO repository (${ARGO_REPO_REF})..."
if [ -d "${ARGO_DIR}/.git" ]; then
  git -C "${ARGO_DIR}" fetch --depth 1 origin "${ARGO_REPO_REF}"
  git -C "${ARGO_DIR}" checkout -f "${ARGO_REPO_REF}"
else
  mkdir -p /opt/argo
  git clone --depth 1 --branch "${ARGO_REPO_REF}" "${ARGO_REPO_URL}" "${ARGO_DIR}"
fi

echo "[argo] Building and starting the ARGO services..."
cd "${ARGO_DIR}"
docker compose up -d --build

echo "[argo] Done. API will be available on TCP port 8000."

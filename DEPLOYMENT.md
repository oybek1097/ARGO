# ARGO Agent — Deployment Guide

This document covers deploying ARGO Agent v3.0 with Docker Compose and
with the Helm chart for Kubernetes.

ARGO consists of two services:

- **argo-core** — the Rust HTTP gateway. Exposes the HTTP API on port
  `8000` (`/api/health`, `/api/chat`, `/api/history`, `/metrics`).
- **argo-brain** — the Python brain. Runs the IPC server on a Unix
  socket and holds the agent loop, tools, and memory.

The two communicate over a Unix domain socket using line-delimited JSON.
Both must therefore share the directory that holds the socket.

## Docker images

| Image | Source | Base | Description |
|---|---|---|---|
| `argo-agent/argo-core` | `argo-core/Dockerfile` | `debian:bookworm-slim` | Multi-stage build: compiles the Rust binary with `cargo build --release`, then ships only the stripped binary. Exposes port `8000`. |
| `argo-agent/argo-brain` | `argo-brain/Dockerfile` | `python:3.12-slim` | Copies the stdlib-only `argo_brain` package and runs `python3 -m argo_brain ipc`. No `pip install` is needed. |

Build the images directly if needed:

```bash
docker build -t argo-agent/argo-core:latest  ./argo-core
docker build -t argo-agent/argo-brain:latest ./argo-brain
```

## Docker Compose

The `docker-compose.yml` at the repository root defines both services,
two shared volumes (`argo-ipc` for the Unix socket, `argo-data` for
persistent data), a `restart: unless-stopped` policy, and a healthcheck
for argo-core hitting `/api/health`.

```bash
# Build the images and start both services.
docker compose up -d --build

# Check status (argo-core should report "healthy").
docker compose ps

# Follow the logs.
docker compose logs -f

# Stop and remove the containers (volumes are kept).
docker compose down

# Stop and also remove the shared volumes.
docker compose down -v
```

Once running, the gateway is reachable on the host:

```bash
curl http://localhost:8000/api/health
```

Both services share the IPC socket via the `argo-ipc` volume mounted at
`/run/argo`, and `ARGO_IPC_SOCKET` is set identically (`/run/argo/argo.sock`)
in both containers.

## Helm chart (Kubernetes)

The Helm chart lives in `helm/argo-agent/`. It deploys argo-core and
argo-brain as two containers in a single pod, sharing an `emptyDir`
volume for the IPC socket and a PersistentVolumeClaim for data. A
`Service` exposes the argo-core HTTP port.

Install:

```bash
helm install argo ./helm/argo-agent
```

Common overrides:

```bash
helm install argo ./helm/argo-agent \
  --set images.core.tag=v3.0.0 \
  --set images.brain.tag=v3.0.0 \
  --set replicaCount=2 \
  --set service.port=8000 \
  --set persistence.size=5Gi
```

Upgrade and uninstall:

```bash
helm upgrade argo ./helm/argo-agent
helm uninstall argo
```

### Key chart values

See `helm/argo-agent/values.yaml` for the full list. Highlights:

| Value | Default | Description |
|---|---|---|
| `replicaCount` | `1` | Number of pod replicas. |
| `images.core.repository` / `images.core.tag` | `argo-agent/argo-core` / `latest` | argo-core image. |
| `images.brain.repository` / `images.brain.tag` | `argo-agent/argo-brain` / `latest` | argo-brain image. |
| `service.type` | `ClusterIP` | Service type for the gateway. |
| `service.port` | `8000` | Service port for the gateway. |
| `ipc.socketPath` | `/run/argo/argo.sock` | Shared Unix IPC socket path. |
| `persistence.enabled` | `true` | Whether to create a PVC for data. |
| `persistence.size` | `1Gi` | Size of the data PVC. |

To reach the gateway from outside the cluster, either set
`service.type=LoadBalancer` / `NodePort`, or port-forward:

```bash
kubectl port-forward svc/argo-argo-core 8000:8000
curl http://localhost:8000/api/health
```

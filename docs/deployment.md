# Deployment

This page summarises how to deploy ARGO and points to the authoritative
[`../DEPLOYMENT.md`](../DEPLOYMENT.md) for the full reference.

ARGO is two services:

- **argo-core** — the Rust HTTP gateway. Exposes the HTTP API on port `8000`
  (`/api/health`, `/api/chat`, `/api/history`, `/metrics`).
- **argo-brain** — the Python brain. Runs the IPC server on a Unix socket and
  holds the agent loop, tools and memory.

They communicate over a **Unix domain socket** using line-delimited JSON, so
both services must share the directory that holds the socket.

> **Single-process option.** The Python brain ships its own HTTP gateway (the
> `serve` command). For small or development deployments you can run just
> `argo-brain` and skip `argo-core` entirely — see [Quickstart](quickstart.md).

## Docker images

| Image | Source | Base |
|---|---|---|
| `argo-agent/argo-core` | `argo-core/Dockerfile` | `debian:bookworm-slim` |
| `argo-agent/argo-brain` | `argo-brain/Dockerfile` | `python:3.12-slim` |

`argo-core`'s Dockerfile is a multi-stage build that compiles the Rust binary
and ships only the stripped result. `argo-brain`'s Dockerfile just copies the
stdlib-only package — there is **no `pip install`** step.

## Docker Compose

The `docker-compose.yml` at the repository root defines both services, two
shared volumes (`argo-ipc` for the Unix socket, `argo-data` for persistent
data), a `restart: unless-stopped` policy and a healthcheck on
`/api/health`.

```bash
docker compose up -d --build      # build images and start both services
docker compose ps                 # argo-core should report "healthy"
docker compose logs -f            # follow logs
docker compose down               # stop (volumes kept)
docker compose down -v            # stop and remove volumes
```

Once up, the gateway is reachable on the host:

```bash
curl http://localhost:8000/api/health
```

Both containers mount the `argo-ipc` volume at `/run/argo` and set
`ARGO_IPC_SOCKET=/run/argo/argo.sock` identically.

## Helm / Kubernetes

The Helm chart is in `helm/argo-agent/`. It runs argo-core and argo-brain as
two containers in a single pod, sharing an `emptyDir` volume for the IPC
socket and a PersistentVolumeClaim for data; a `Service` exposes the gateway.

```bash
helm install argo ./helm/argo-agent

helm install argo ./helm/argo-agent \
  --set images.core.tag=v3.0.0 \
  --set images.brain.tag=v3.0.0 \
  --set replicaCount=2 \
  --set persistence.size=5Gi

helm upgrade argo ./helm/argo-agent
helm uninstall argo
```

### Key chart values

| Value | Default | Description |
|---|---|---|
| `replicaCount` | `1` | Pod replicas. |
| `images.core.repository` / `.tag` | `argo-agent/argo-core` / `latest` | argo-core image. |
| `images.brain.repository` / `.tag` | `argo-agent/argo-brain` / `latest` | argo-brain image. |
| `service.type` | `ClusterIP` | Gateway service type. |
| `service.port` | `8000` | Gateway service port. |
| `ipc.socketPath` | `/run/argo/argo.sock` | Shared IPC socket path. |
| `persistence.enabled` | `true` | Create a data PVC. |
| `persistence.size` | `1Gi` | Data PVC size. |

To reach the gateway from outside the cluster, set `service.type` to
`LoadBalancer` or `NodePort`, or port-forward:

```bash
kubectl port-forward svc/argo-argo-core 8000:8000
curl http://localhost:8000/api/health
```

## Cloud options

ARGO is intentionally infrastructure-neutral and on-premises friendly:

- **Any container host.** Because both services are plain containers, the
  Compose file runs unchanged on a single VM (cloud or bare metal).
- **Managed Kubernetes.** The Helm chart works on any conformant cluster —
  EKS, GKE, AKS or a self-managed cluster. Use a `LoadBalancer` service or an
  Ingress to expose the gateway.
- **Sovereign / air-gapped.** The brain is stdlib-only with no network
  dependency for its core loop, and the `MockProvider` needs no API key —
  ARGO can run fully offline. For a real LLM, point a provider at an
  on-premises endpoint (e.g. an OpenAI-compatible or Ollama server; see
  [Configuration](configuration.md)).

## Production checklist

- Run `python3 -m argo_brain doctor` (or exec it in the brain container) to
  confirm the install is healthy.
- Set a real LLM provider via the `model` setting and the matching API-key
  environment variable — see [Configuration](configuration.md).
- Persist the data volume / PVC so memory and the Kanban board survive
  restarts.
- Scrape `/metrics` (Prometheus format) from `argo-core` for monitoring.
- Keep the gateway behind a reverse proxy or Ingress with TLS if it is exposed
  beyond localhost.

## See also

- Full reference: [`../DEPLOYMENT.md`](../DEPLOYMENT.md).
- [Architecture](architecture.md) — why the two services need a shared socket.
- [Troubleshooting](troubleshooting.md) — IPC socket and deployment problems.

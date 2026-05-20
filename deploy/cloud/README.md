# ARGO Agent — One-Click Cloud Deployment

This directory contains one-click deployment templates for running ARGO
Agent v3.0 on five cloud providers:

| Provider | Directory | Mechanism |
|---|---|---|
| Amazon Web Services | [`aws/`](aws/) | CloudFormation stack (EC2 + security group + UserData) |
| Google Cloud Platform | [`gcp/`](gcp/) | Deployment Manager config (Compute Engine VM + firewall) |
| DigitalOcean | [`digitalocean/`](digitalocean/) | `doctl` Droplet with cloud-config user-data |
| Yandex Cloud | [`yandex/`](yandex/) | Terraform (compute instance + security group) |
| Tencent Cloud | [`tencent/`](tencent/) | Terraform (CVM instance + security group) |

> **Project status:** ARGO is alpha software approaching its v3.0 GA
> release. These templates are intended for evaluation, demos, and
> small single-node deployments. For production / multi-node use, see
> the Helm chart in [`helm/argo-agent/`](../../helm/argo-agent/) and the
> main [`DEPLOYMENT.md`](../../DEPLOYMENT.md).

## Common architecture

Every template provisions the **same thing**: a single small Linux VM
that runs both ARGO services with Docker Compose.

```
            Internet
               │
        ┌──────┴───────┐
        │  Cloud VM    │   (Ubuntu 22.04 LTS)
        │              │
        │  Docker      │
        │  ┌─────────┐ │
        │  │argo-core│ │ ── HTTP :8000  (open to the Internet)
        │  └────┬────┘ │
        │   IPC │ socket (shared volume)
        │  ┌────┴────┐ │
        │  │argo-brain│ │
        │  └─────────┘ │
        └──────────────┘
```

`argo-core` (Rust gateway) and `argo-brain` (Python brain) run as the
two services defined in the repository-root [`docker-compose.yml`](../../docker-compose.yml).
They share a Unix-socket volume for IPC and a data volume for the SQLite
database. The cloud firewall / security group opens only:

- **TCP 8000** — the ARGO HTTP API.
- **TCP 22** — SSH for administration.

## How the templates work

On first boot the VM runs a startup script (cloud-init UserData /
startup-script / cloud-config) that:

1. Installs Docker Engine and the Docker Compose plugin.
2. Clones the ARGO repository (default branch `main`).
3. Runs `docker compose up -d --build` from the repository root.

The shared, provider-agnostic version of this script is
[`cloud-init.yaml`](cloud-init.yaml); each provider directory adapts it
to that provider's metadata format.

## Minimum instance sizing

The first boot performs a multi-stage Rust build (`cargo build
--release`), which is the most resource-intensive step.

| Use case | vCPU | RAM | Disk | Example instance type |
|---|---|---|---|---|
| Minimum (build + run) | 2 | 4 GB | 20 GB | AWS `t3.medium`, GCP `e2-medium`, DO `s-2vcpu-4gb`, Yandex 2×100% / 4 GB, Tencent `S5.MEDIUM4` |
| Comfortable | 2 | 8 GB | 30 GB | AWS `t3.large`, GCP `e2-standard-2` |

A 1 GB / 1 vCPU instance is **not** recommended — the Rust build is
likely to be killed by the OOM reaper. If you must use a very small
instance, build the images elsewhere and pull pre-built images instead
of building on the VM.

> First boot typically takes **5–10 minutes** while Docker installs and
> the images build. The API is not reachable until that finishes.

## Post-deploy verification

Once the VM has finished its startup script, verify the deployment from
your workstation (replace `<ip>` with the VM's public IP address):

```bash
curl http://<ip>:8000/api/health
```

A healthy gateway responds with HTTP `200` and a small JSON body. If the
request times out or is refused, the startup script is probably still
running — wait a few minutes and retry. To inspect progress, SSH into
the VM and run:

```bash
# Provider startup-script logs (cloud-init):
sudo tail -f /var/log/cloud-init-output.log

# Once containers exist:
cd /opt/argo/ARGO && sudo docker compose ps
sudo docker compose logs -f
```

## Security notes

These templates favour a fast first-run experience over a hardened
posture. Before exposing an instance long-term you should:

- Restrict the SSH (port 22) source range to your own IP.
- Put the API behind TLS (a reverse proxy such as Caddy or Nginx, or a
  cloud load balancer) instead of serving plain HTTP on port 8000.
- Pin the deployment to a tagged release instead of the `main` branch.

## Tearing down

- **AWS:** delete the CloudFormation stack.
- **GCP:** `gcloud deployment-manager deployments delete argo`.
- **DigitalOcean:** `doctl compute droplet delete argo-agent`.
- **Yandex / Tencent:** `terraform destroy`.

# ARGO Agent on Google Cloud Platform

One-click deployment of ARGO Agent v3.0 to a single Compute Engine VM.
Two equivalent paths are provided — pick whichever fits your workflow:

- **`gcloud` startup script** — a single `gcloud compute instances create`
  command that attaches [`startup-script.sh`](startup-script.sh).
- **Deployment Manager** — [`argo-gcp.yaml`](argo-gcp.yaml), which also
  creates the firewall rule as part of the deployment.

Both provision the same thing: an Ubuntu 22.04 LTS VM (default
`e2-medium`, 2 vCPU / 4 GB) that installs Docker, clones the ARGO
repository, and runs `docker compose up -d --build`.

## Prerequisites

- A GCP project with billing enabled.
- The [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) installed
  and authenticated (`gcloud auth login`, `gcloud config set project ...`).

## Option A — gcloud startup script (one command)

```bash
gcloud compute instances create argo-agent \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --tags=argo-agent \
  --metadata=argo-repo-ref=main \
  --metadata-from-file=startup-script=startup-script.sh
```

Then create the firewall rule (once per project):

```bash
gcloud compute firewall-rules create argo-agent-allow \
  --direction=INGRESS --action=ALLOW \
  --rules=tcp:22,tcp:8000 \
  --target-tags=argo-agent \
  --source-ranges=0.0.0.0/0
```

## Option B — Deployment Manager

The config bundles the VM and firewall rule together:

```bash
gcloud deployment-manager deployments create argo --config argo-gcp.yaml
```

## Get the instance address

```bash
gcloud compute instances describe argo-agent --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

## Verify

First boot takes about 5–10 minutes (Docker install + Rust build). Then:

```bash
curl http://<EXTERNAL_IP>:8000/api/health
```

A healthy gateway returns HTTP `200`. To watch progress:

```bash
gcloud compute ssh argo-agent --zone=us-central1-a \
  --command='sudo journalctl -u google-startup-scripts -f'
```

## Tear down

Option A:

```bash
gcloud compute instances delete argo-agent --zone=us-central1-a
gcloud compute firewall-rules delete argo-agent-allow
```

Option B:

```bash
gcloud deployment-manager deployments delete argo
```

> **Note:** ARGO is alpha software approaching its GA release. The
> firewall rule above opens ports `22` and `8000` to `0.0.0.0/0` for a
> fast first run — narrow `--source-ranges` and front the API with TLS
> for anything longer-lived.

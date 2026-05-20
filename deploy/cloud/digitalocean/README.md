# ARGO Agent on DigitalOcean

One-click deployment of ARGO Agent v3.0 to a single DigitalOcean Droplet
using the [`argo-droplet.yaml`](argo-droplet.yaml) cloud-config.

The cloud-config installs Docker, clones the ARGO repository, and runs
`docker compose up -d --build` on first boot — both ARGO services
(argo-core + argo-brain) come up automatically, with the HTTP API on
TCP port `8000`.

## Prerequisites

- A DigitalOcean account.
- The [`doctl` CLI](https://docs.digitalocean.com/reference/doctl/how-to/install/)
  installed and authenticated (`doctl auth init`).
- An SSH key registered with DigitalOcean. List your key fingerprints
  with `doctl compute ssh-key list`.

## Deploy (one command)

```bash
doctl compute droplet create argo-agent \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region fra1 \
  --ssh-keys YOUR_SSH_KEY_FINGERPRINT \
  --user-data-file argo-droplet.yaml \
  --wait
```

`s-2vcpu-4gb` (2 vCPU / 4 GB) is the recommended minimum — the first
boot compiles `argo-core` from source.

## Open the firewall

DigitalOcean Droplets have no inbound firewall by default, so port
`8000` is already reachable. To add an explicit cloud firewall:

```bash
doctl compute firewall create \
  --name argo-agent-fw \
  --inbound-rules "protocol:tcp,ports:22,address:0.0.0.0/0 protocol:tcp,ports:8000,address:0.0.0.0/0" \
  --outbound-rules "protocol:tcp,ports:all,address:0.0.0.0/0 protocol:udp,ports:all,address:0.0.0.0/0" \
  --droplet-ids YOUR_DROPLET_ID
```

## Get the Droplet address

```bash
doctl compute droplet get argo-agent --format PublicIPv4 --no-header
```

## Verify

First boot takes about 5–10 minutes (Docker install + Rust build). Then:

```bash
curl http://<DROPLET_IP>:8000/api/health
```

A healthy gateway returns HTTP `200`. To watch progress, SSH in:

```bash
ssh root@<DROPLET_IP>
tail -f /var/log/cloud-init-output.log
```

## Marketplace 1-Click image (notes)

DigitalOcean's [Marketplace](https://marketplace.digitalocean.com/) lets
vendors publish a 1-Click image so users can launch a pre-configured
Droplet with no user-data step. To package ARGO as a 1-Click app:

1. Build a base Droplet snapshot with Docker and the ARGO repository
   pre-installed under `/opt/argo/ARGO` (the steps in
   `argo-droplet.yaml` are the build recipe).
2. Add a `systemd` unit (or a DigitalOcean `90-argo` first-boot script)
   that runs `docker compose up -d` from `/opt/argo/ARGO` on first boot.
3. Include the standard Marketplace files: a vendor logo, a
   `description`, and the recommended droplet size (`s-2vcpu-4gb`).
4. Submit the snapshot through the
   [DigitalOcean Vendor Portal](https://marketplace.digitalocean.com/vendors).

Until an official 1-Click listing exists, the `doctl` + cloud-config
flow above is the supported path.

## Tear down

```bash
doctl compute droplet delete argo-agent
```

> **Note:** ARGO is alpha software approaching its GA release. The
> example firewall opens ports `22` and `8000` to `0.0.0.0/0` for a fast
> first run — narrow the inbound `address` ranges and front the API with
> TLS for anything longer-lived.

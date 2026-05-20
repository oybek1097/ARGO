# ARGO Agent on Yandex Cloud (Terraform)

One-click deployment of ARGO Agent v3.0 to a single Yandex Cloud Compute
instance using Terraform.

Yandex Cloud is a deliberate first-class target for ARGO: the project is
aimed at Central Asian and sovereign-deployment scenarios, where Yandex
Cloud is a common platform.

The Terraform config provisions:

- A dedicated **VPC network and subnet**.
- A **security group** opening TCP `8000` (HTTP API) and TCP `22` (SSH).
- A **Compute instance** (default 2 vCPU / 4 GB, Ubuntu 22.04 LTS) that
  runs the shared [`cloud-init.yaml`](../cloud-init.yaml): install Docker,
  clone the ARGO repository, `docker compose up -d --build`.

## Prerequisites

- A Yandex Cloud account, a **cloud ID** and a **folder ID**.
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.3.
- The [`yc` CLI](https://yandex.cloud/docs/cli/quickstart) (recommended
  for obtaining a token), or an IAM/OAuth token.
- An SSH key pair (the public key path is set via `ssh_public_key_path`).

## Configure

Export your credentials, or create a `terraform.tfvars` file:

```hcl
# terraform.tfvars
yc_cloud_id         = "b1gxxxxxxxxxxxxxxxxx"
yc_folder_id        = "b1gyyyyyyyyyyyyyyyyy"
yc_zone             = "ru-central1-a"
ssh_public_key_path = "~/.ssh/id_rsa.pub"
```

A token can be supplied via the `YC_TOKEN` environment variable:

```bash
export YC_TOKEN=$(yc iam create-token)
```

## Deploy (one command)

```bash
terraform init && terraform apply
```

Terraform prints the `argo_public_ip` and `health_check_url` outputs once
the instance is created.

## Verify

First boot takes about 5–10 minutes (Docker install + Rust build). Then:

```bash
curl http://<argo_public_ip>:8000/api/health
```

A healthy gateway returns HTTP `200`. To watch progress, SSH in:

```bash
ssh ubuntu@<argo_public_ip>
sudo tail -f /var/log/cloud-init-output.log
```

## Key variables

| Variable | Default | Description |
|---|---|---|
| `yc_cloud_id` | _(required)_ | Yandex Cloud cloud ID. |
| `yc_folder_id` | _(required)_ | Yandex Cloud folder ID. |
| `yc_zone` | `ru-central1-a` | Availability zone. |
| `instance_cores` | `2` | vCPU cores. |
| `instance_memory_gb` | `4` | Memory in GiB. |
| `disk_size_gb` | `20` | Boot disk size in GiB. |
| `ssh_public_key_path` | `~/.ssh/id_rsa.pub` | SSH public key file. |
| `ssh_cidr` | `0.0.0.0/0` | CIDR allowed to reach SSH. |
| `api_cidr` | `0.0.0.0/0` | CIDR allowed to reach the HTTP API. |
| `preemptible` | `false` | Use a cheaper preemptible instance. |

## Tear down

```bash
terraform destroy
```

> **Note:** ARGO is alpha software approaching its GA release. The
> defaults open ports `22` and `8000` to `0.0.0.0/0` for a fast first
> run — narrow `ssh_cidr` / `api_cidr` and front the API with TLS for
> anything longer-lived.

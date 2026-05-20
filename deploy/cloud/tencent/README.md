# ARGO Agent on Tencent Cloud (Terraform)

One-click deployment of ARGO Agent v3.0 to a single Tencent Cloud CVM
(Cloud Virtual Machine) instance using Terraform.

The Terraform config provisions:

- A dedicated **VPC and subnet**.
- A **security group** opening TCP `8000` (HTTP API) and TCP `22` (SSH).
- A **CVM instance** (default `S5.MEDIUM4`, 2 vCPU / 4 GB, Ubuntu 22.04
  LTS) that runs the shared [`cloud-init.yaml`](../cloud-init.yaml):
  install Docker, clone the ARGO repository, `docker compose up -d --build`.

## Prerequisites

- A Tencent Cloud account and an API key pair
  (**SecretId** / **SecretKey**) from the
  [CAM console](https://console.tencentcloud.com/cam/capi).
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.3.
- Optionally, an existing Tencent Cloud SSH key pair for SSH access
  (its ID looks like `skey-xxxxxxxx`).

## Configure

Export your credentials, or create a `terraform.tfvars` file:

```bash
export TENCENTCLOUD_SECRET_ID="AKIDxxxxxxxxxxxxxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxxxxxxxxxxxxxxxxx"
```

```hcl
# terraform.tfvars
region = "ap-singapore"
key_id = "skey-xxxxxxxx"   # optional, for SSH access
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
| `secret_id` | _(env)_ | API SecretId — or use `TENCENTCLOUD_SECRET_ID`. |
| `secret_key` | _(env)_ | API SecretKey — or use `TENCENTCLOUD_SECRET_KEY`. |
| `region` | `ap-singapore` | Tencent Cloud region. |
| `instance_type` | `S5.MEDIUM4` | CVM instance type (2 vCPU / 4 GB minimum). |
| `disk_size_gb` | `50` | System disk size in GiB. |
| `bandwidth_mbps` | `10` | Public egress bandwidth cap. |
| `key_id` | _(empty)_ | Existing SSH key pair ID to attach. |
| `ssh_cidr` | `0.0.0.0/0` | CIDR allowed to reach SSH. |
| `api_cidr` | `0.0.0.0/0` | CIDR allowed to reach the HTTP API. |

## Tear down

```bash
terraform destroy
```

> **Note:** ARGO is alpha software approaching its GA release. The
> defaults open ports `22` and `8000` to `0.0.0.0/0` for a fast first
> run — narrow `ssh_cidr` / `api_cidr` and front the API with TLS for
> anything longer-lived.

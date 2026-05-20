# ARGO Agent on AWS (CloudFormation)

One-click deployment of ARGO Agent v3.0 to a single Amazon EC2 instance
using the [`argo-cloudformation.yaml`](argo-cloudformation.yaml) template.

The stack provisions:

- An **EC2 instance** (default `t3.medium`, Ubuntu 22.04 LTS).
- A **security group** opening TCP `8000` (HTTP API) and TCP `22` (SSH).
- **UserData** that installs Docker, clones the ARGO repository, and runs
  `docker compose up -d --build` — the same steps as the shared
  [`cloud-init.yaml`](../cloud-init.yaml).

## Prerequisites

- An AWS account and the [AWS CLI](https://aws.amazon.com/cli/) configured
  (`aws configure`).
- An existing **EC2 key pair** in the target region (for SSH access).

## Deploy (one command)

```bash
aws cloudformation create-stack \
  --stack-name argo-agent \
  --template-body file://argo-cloudformation.yaml \
  --parameters ParameterKey=KeyName,ParameterValue=YOUR_KEY_PAIR_NAME
```

Wait for the stack to reach `CREATE_COMPLETE`:

```bash
aws cloudformation wait stack-create-complete --stack-name argo-agent
```

You can also deploy via the AWS Console: **CloudFormation → Create stack →
Upload a template file**, then select `argo-cloudformation.yaml`.

## Get the instance address

```bash
aws cloudformation describe-stacks --stack-name argo-agent \
  --query "Stacks[0].Outputs"
```

The `PublicIp` and `HealthCheckUrl` outputs give you the address.

## Verify

First boot takes about 5–10 minutes (Docker install + Rust build). Then:

```bash
curl http://<PublicIp>:8000/api/health
```

A healthy gateway returns HTTP `200`. To watch progress, SSH in:

```bash
ssh ubuntu@<PublicIp>
sudo tail -f /var/log/argo-userdata.log
```

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `InstanceType` | `t3.medium` | EC2 instance type (2 vCPU / 4 GB minimum). |
| `KeyName` | _(required)_ | Existing EC2 key pair for SSH. |
| `SSHLocation` | `0.0.0.0/0` | CIDR allowed to reach SSH — narrow this. |
| `ApiLocation` | `0.0.0.0/0` | CIDR allowed to reach the HTTP API. |
| `ArgoRepoUrl` | `https://github.com/argo-agent/argo.git` | Git repo to clone. |
| `ArgoRepoRef` | `main` | Branch or tag to deploy. |
| `VolumeSizeGb` | `20` | Root EBS volume size (GiB). |

> The template ships a region-to-AMI map for common regions. If your
> region is not listed, add its Ubuntu 22.04 LTS (amd64) AMI ID to the
> `RegionAmi` mapping.

## Tear down

```bash
aws cloudformation delete-stack --stack-name argo-agent
```

This removes the instance, the security group, and the EBS volume.

> **Note:** ARGO is alpha software approaching its GA release, and this
> template favours a fast first run. For long-term use, narrow the
> security group, put the API behind TLS, and pin `ArgoRepoRef` to a
> tagged release.

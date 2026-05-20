# ===========================================================================
# ARGO Agent v3.0 — Tencent Cloud deployment (Terraform).
#
# Provisions a single CVM (Cloud Virtual Machine) instance running both
# ARGO services (argo-core + argo-brain) via Docker Compose, in a
# dedicated VPC / subnet, with a security group that opens TCP 8000
# (HTTP API) and TCP 22 (SSH).
#
# Usage:
#   terraform init
#   terraform apply
#   curl http://<output: argo_public_ip>:8000/api/health
# ===========================================================================

terraform {
  required_version = ">= 1.3"

  required_providers {
    tencentcloud = {
      source  = "tencentcloudstack/tencentcloud"
      version = ">= 1.81.0"
    }
  }
}

provider "tencentcloud" {
  # Credentials are read from the TENCENTCLOUD_SECRET_ID /
  # TENCENTCLOUD_SECRET_KEY environment variables, or set explicitly.
  secret_id  = var.secret_id != "" ? var.secret_id : null
  secret_key = var.secret_key != "" ? var.secret_key : null
  region     = var.region
}

# --- Availability zones -----------------------------------------------------
data "tencentcloud_availability_zones" "zones" {}

# --- Latest Ubuntu 22.04 LTS image -----------------------------------------
data "tencentcloud_images" "ubuntu" {
  image_type       = ["PUBLIC_IMAGE"]
  os_name          = "Ubuntu Server 22.04 LTS 64bit"
  result_output_file = ""
}

# --- VPC and subnet ---------------------------------------------------------
resource "tencentcloud_vpc" "argo" {
  name       = "argo-agent-vpc"
  cidr_block = "10.20.0.0/16"
}

resource "tencentcloud_subnet" "argo" {
  name              = "argo-agent-subnet"
  vpc_id            = tencentcloud_vpc.argo.id
  cidr_block        = "10.20.1.0/24"
  availability_zone = data.tencentcloud_availability_zones.zones.zones.0.name
}

# --- Security group ---------------------------------------------------------
resource "tencentcloud_security_group" "argo" {
  name        = "argo-agent-sg"
  description = "ARGO Agent — allow SSH (22) and the HTTP API (8000)."
}

resource "tencentcloud_security_group_rule" "ssh" {
  security_group_id = tencentcloud_security_group.argo.id
  type              = "ingress"
  cidr_ip           = var.ssh_cidr
  ip_protocol       = "tcp"
  port_range        = "22"
  policy            = "ACCEPT"
  description       = "SSH administration access."
}

resource "tencentcloud_security_group_rule" "api" {
  security_group_id = tencentcloud_security_group.argo.id
  type              = "ingress"
  cidr_ip           = var.api_cidr
  ip_protocol       = "tcp"
  port_range        = "8000"
  policy            = "ACCEPT"
  description       = "ARGO HTTP API (argo-core gateway)."
}

resource "tencentcloud_security_group_rule" "egress" {
  security_group_id = tencentcloud_security_group.argo.id
  type              = "egress"
  cidr_ip           = "0.0.0.0/0"
  ip_protocol       = "tcp"
  port_range        = "ALL"
  policy            = "ACCEPT"
  description       = "Allow all outbound traffic (Docker pulls, git clone)."
}

# --- CVM instance -----------------------------------------------------------
resource "tencentcloud_instance" "argo" {
  instance_name              = "argo-agent"
  availability_zone          = data.tencentcloud_availability_zones.zones.zones.0.name
  image_id                   = data.tencentcloud_images.ubuntu.images.0.image_id
  instance_type              = var.instance_type
  vpc_id                     = tencentcloud_vpc.argo.id
  subnet_id                  = tencentcloud_subnet.argo.id
  security_groups            = [tencentcloud_security_group.argo.id]
  allocate_public_ip         = true
  internet_max_bandwidth_out = var.bandwidth_mbps

  system_disk_type = "CLOUD_PREMIUM"
  system_disk_size = var.disk_size_gb

  # Inject an SSH public key for the default user.
  key_ids = var.key_id != "" ? [var.key_id] : null

  # user_data must be base64-encoded; it runs the same steps as the
  # shared deploy/cloud/cloud-init.yaml.
  user_data = base64encode(file("${path.module}/../cloud-init.yaml"))
}

# --- Outputs ----------------------------------------------------------------
output "argo_public_ip" {
  description = "Public IPv4 address of the ARGO instance."
  value       = tencentcloud_instance.argo.public_ip
}

output "health_check_url" {
  description = "ARGO HTTP API health endpoint (allow a few minutes for first boot)."
  value       = "http://${tencentcloud_instance.argo.public_ip}:8000/api/health"
}

output "ssh_command" {
  description = "SSH command to reach the instance."
  value       = "ssh ubuntu@${tencentcloud_instance.argo.public_ip}"
}

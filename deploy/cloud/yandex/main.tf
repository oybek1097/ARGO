# ===========================================================================
# ARGO Agent v3.0 — Yandex Cloud deployment (Terraform).
#
# Provisions a single Compute Cloud instance running both ARGO services
# (argo-core + argo-brain) via Docker Compose, in a dedicated network /
# subnet, with a security group that opens TCP 8000 (HTTP API) and
# TCP 22 (SSH).
#
# Yandex Cloud is a first-class target for ARGO: the project is aimed at
# Central Asian and sovereign-deployment scenarios.
#
# Usage:
#   terraform init
#   terraform apply
#   curl http://<output: argo_public_ip>:8000/api/health
# ===========================================================================

terraform {
  required_version = ">= 1.3"

  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = ">= 0.100.0"
    }
  }
}

provider "yandex" {
  # Authentication is read from the YC_TOKEN / YC_CLOUD_ID / YC_FOLDER_ID
  # environment variables, or set explicitly via the variables below.
  token     = var.yc_token != "" ? var.yc_token : null
  cloud_id  = var.yc_cloud_id
  folder_id = var.yc_folder_id
  zone      = var.yc_zone
}

# --- Latest Ubuntu 22.04 LTS image -----------------------------------------
data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2204-lts"
}

# --- Network ----------------------------------------------------------------
resource "yandex_vpc_network" "argo" {
  name = "argo-agent-net"
}

resource "yandex_vpc_subnet" "argo" {
  name           = "argo-agent-subnet"
  zone           = var.yc_zone
  network_id     = yandex_vpc_network.argo.id
  v4_cidr_blocks = ["10.10.0.0/24"]
}

# --- Security group ---------------------------------------------------------
resource "yandex_vpc_security_group" "argo" {
  name        = "argo-agent-sg"
  description = "ARGO Agent — allow SSH (22) and the HTTP API (8000)."
  network_id  = yandex_vpc_network.argo.id

  ingress {
    description    = "SSH administration access."
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = [var.ssh_cidr]
  }

  ingress {
    description    = "ARGO HTTP API (argo-core gateway)."
    protocol       = "TCP"
    port           = 8000
    v4_cidr_blocks = [var.api_cidr]
  }

  egress {
    description    = "Allow all outbound traffic (Docker pulls, git clone)."
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- Compute instance -------------------------------------------------------
resource "yandex_compute_instance" "argo" {
  name        = "argo-agent"
  platform_id = "standard-v3"
  zone        = var.yc_zone

  resources {
    cores  = var.instance_cores
    memory = var.instance_memory_gb
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = var.disk_size_gb
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.argo.id
    nat                = true # assign an ephemeral public IP
    security_group_ids = [yandex_vpc_security_group.argo.id]
  }

  metadata = {
    # Yandex Cloud supports cloud-init via the user-data metadata key.
    user-data = templatefile("${path.module}/../cloud-init.yaml", {})
    # SSH public key for the default `ubuntu` user.
    ssh-keys = "ubuntu:${file(var.ssh_public_key_path)}"
  }

  scheduling_policy {
    # Set to true for a cheaper preemptible instance (evaluation only).
    preemptible = var.preemptible
  }
}

# --- Outputs ----------------------------------------------------------------
output "argo_public_ip" {
  description = "Public IPv4 address of the ARGO instance."
  value       = yandex_compute_instance.argo.network_interface.0.nat_ip_address
}

output "health_check_url" {
  description = "ARGO HTTP API health endpoint (allow a few minutes for first boot)."
  value       = "http://${yandex_compute_instance.argo.network_interface.0.nat_ip_address}:8000/api/health"
}

output "ssh_command" {
  description = "SSH command to reach the instance."
  value       = "ssh ubuntu@${yandex_compute_instance.argo.network_interface.0.nat_ip_address}"
}

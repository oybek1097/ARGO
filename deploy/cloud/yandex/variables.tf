# ===========================================================================
# ARGO Agent v3.0 — Yandex Cloud deployment variables.
# ===========================================================================

variable "yc_token" {
  description = <<-EOT
    Yandex Cloud OAuth or IAM token. Leave empty to authenticate via the
    YC_TOKEN environment variable or `yc` CLI credentials.
  EOT
  type        = string
  default     = ""
  sensitive   = true
}

variable "yc_cloud_id" {
  description = "Yandex Cloud cloud ID."
  type        = string
}

variable "yc_folder_id" {
  description = "Yandex Cloud folder ID."
  type        = string
}

variable "yc_zone" {
  description = "Availability zone for the instance and subnet."
  type        = string
  default     = "ru-central1-a"
}

variable "instance_cores" {
  description = "Number of vCPU cores. 2 is the recommended minimum."
  type        = number
  default     = 2
}

variable "instance_memory_gb" {
  description = "Instance memory in GiB. 4 is the recommended minimum."
  type        = number
  default     = 4
}

variable "disk_size_gb" {
  description = "Boot disk size in GiB."
  type        = number
  default     = 20
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key file added to the `ubuntu` user."
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_cidr" {
  description = "CIDR range allowed to reach SSH (port 22). Narrow this in production."
  type        = string
  default     = "0.0.0.0/0"
}

variable "api_cidr" {
  description = "CIDR range allowed to reach the ARGO HTTP API (port 8000)."
  type        = string
  default     = "0.0.0.0/0"
}

variable "preemptible" {
  description = "If true, provision a cheaper preemptible instance (evaluation only)."
  type        = bool
  default     = false
}

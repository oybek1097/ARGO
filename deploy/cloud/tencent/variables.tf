# ===========================================================================
# ARGO Agent v3.0 — Tencent Cloud deployment variables.
# ===========================================================================

variable "secret_id" {
  description = <<-EOT
    Tencent Cloud API SecretId. Leave empty to authenticate via the
    TENCENTCLOUD_SECRET_ID environment variable.
  EOT
  type        = string
  default     = ""
  sensitive   = true
}

variable "secret_key" {
  description = <<-EOT
    Tencent Cloud API SecretKey. Leave empty to authenticate via the
    TENCENTCLOUD_SECRET_KEY environment variable.
  EOT
  type        = string
  default     = ""
  sensitive   = true
}

variable "region" {
  description = "Tencent Cloud region for all resources."
  type        = string
  default     = "ap-singapore"
}

variable "instance_type" {
  description = <<-EOT
    CVM instance type. S5.MEDIUM4 (2 vCPU / 4 GB) is the recommended
    minimum, since the first boot compiles argo-core from source.
  EOT
  type        = string
  default     = "S5.MEDIUM4"
}

variable "disk_size_gb" {
  description = "System disk size in GiB."
  type        = number
  default     = 50
}

variable "bandwidth_mbps" {
  description = "Public network egress bandwidth cap in Mbps."
  type        = number
  default     = 10
}

variable "key_id" {
  description = <<-EOT
    ID of an existing Tencent Cloud SSH key pair (e.g. "skey-xxxxxxxx")
    to attach for SSH access. Leave empty to skip key injection.
  EOT
  type        = string
  default     = ""
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

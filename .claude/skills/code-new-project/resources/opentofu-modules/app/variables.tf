# No defaults on purpose — an unconfigured `tofu apply` should fail loudly
# instead of provisioning into the wrong project. Set these per-environment
# in environments/<env>/terraform.tfvars.

variable "environment" {
  description = "Environment name (staging|prod) — used to derive resource names and Neon branch"
  type        = string
  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be \"staging\" or \"prod\"."
  }
}

variable "project_name" {
  description = "Short, DNS-safe project name used to derive resource names"
  type        = string
}

variable "gcp_project_id" {
  description = "GCP project ID to deploy Cloud Run into — a SEPARATE GCP project per environment is the recommended default (see reference.md's multi-environment section), not one project with env-suffixed resources"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for Cloud Run (pick close to Neon's region to minimize DB latency)"
  type        = string
  default     = "us-central1"
}

variable "container_image" {
  description = "Fully-qualified container image for the Cloud Run service (e.g. from Artifact Registry) — passed as -var from CI at deploy time, not committed to a .tfvars file"
  type        = string
}

variable "neon_org_id" {
  description = "Neon organization ID (from the Neon console)"
  type        = string
}

variable "neon_project_id" {
  description = "Existing Neon project ID — this module creates a BRANCH within it, not a new project. One Neon project is shared across environments via branching (staging = persistent branch, prod = main branch); see reference.md for why."
  type        = string
}

variable "neon_parent_branch_id" {
  description = "Neon branch ID to fork from when creating this environment's branch (typically the prod/main branch's ID)"
  type        = string
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID that owns the R2 bucket"
  type        = string
}

variable "gcp_project_id" {
  type = string
}
variable "gcp_region" {
  type    = string
  default = "us-central1"
}
variable "container_image" {
  type = string
}

module "app" {
  source = "../../modules/app"

  environment           = "staging"
  project_name          = "TODO-your-project-name"
  gcp_project_id        = var.gcp_project_id
  gcp_region            = var.gcp_region
  container_image       = var.container_image
  neon_org_id           = "TODO-your-neon-org-id"
  neon_project_id       = "TODO-your-neon-project-id"
  neon_parent_branch_id = "TODO-prod-branch-id-to-fork-staging-from"
  cloudflare_account_id = "TODO-your-cloudflare-account-id"
}

output "cloud_run_url" {
  value = module.app.cloud_run_url
}

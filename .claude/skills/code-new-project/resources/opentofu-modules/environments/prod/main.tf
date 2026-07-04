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

# KNOWN SIMPLIFICATION: this module always creates a NEW Neon branch,
# which for prod means "prod" becomes a child branch forked from
# neon_parent_branch_id rather than being the project's actual default
# branch. That's fine if you're OK with prod living on its own named
# branch (common, and keeps prod/staging/dev symmetrical in the module).
# If you'd rather have "prod" mean the project's literal default branch,
# use a `data "neon_project"` block to read `default_branch_id` and skip
# branch creation for this environment instead — not implemented here,
# flagged rather than guessed at, since it changes the module's shape.
module "app" {
  source = "../../modules/app"

  environment           = "prod"
  project_name          = "TODO-your-project-name"
  gcp_project_id        = var.gcp_project_id
  gcp_region            = var.gcp_region
  container_image       = var.container_image
  neon_org_id           = "TODO-your-neon-org-id"
  neon_project_id       = "TODO-your-neon-project-id"
  neon_parent_branch_id = "TODO-neon-projects-default-branch-id"
  cloudflare_account_id = "TODO-your-cloudflare-account-id"
}

output "cloud_run_url" {
  value = module.app.cloud_run_url
}

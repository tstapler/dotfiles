# Child modules using non-default-namespace providers must declare their
# own required_providers block (source only, no version constraint or
# provider config — those belong in the calling environment's root
# versions.tf) or Terraform assumes the default hashicorp/ namespace and
# fails to resolve cloudflare/neon. Discovered via `terraform init`
# during scaffold authoring, not a guess.

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
    cloudflare = {
      source = "cloudflare/cloudflare"
    }
    neon = {
      source = "kislerdm/neon"
    }
  }
}

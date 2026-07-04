terraform {
  required_version = ">= 1.7.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    # Community Neon provider — no official provider exists. Verified
    # against v0.13.0 during scaffold authoring; re-check before bumping
    # the version constraint.
    neon = {
      source  = "kislerdm/neon"
      version = "~> 0.13"
    }
  }

  # OpenTofu 1.8+ supports variables in backend config — still needs a
  # real bucket name filled in per environment; this directory boundary
  # (not a shared workspace) IS the isolation mechanism, see
  # reference.md's multi-environment section for why.
  # backend "gcs" {
  #   bucket = "TODO-your-tofu-state-bucket"
  #   prefix = "staging/state"
  # }
}

# Separate GCP project per environment is the recommended default (not
# one project with env-suffixed resources) — see reference.md.
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "cloudflare" {
  # Reads CLOUDFLARE_API_TOKEN from env — do not hardcode.
}

provider "neon" {
  # Reads NEON_API_KEY from env — do not hardcode.
}

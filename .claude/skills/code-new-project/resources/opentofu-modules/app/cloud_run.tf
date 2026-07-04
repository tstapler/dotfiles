# GCP Cloud Run service — true scale-to-zero (min_instance_count = 0),
# default CPU-during-requests billing. See reference.md for why this beat
# App Runner/Fargate. Schema verified against hashicorp/google v6.50.0 via
# `terraform providers schema -json` during scaffold authoring.

resource "google_cloud_run_v2_service" "api" {
  name     = "${var.project_name}-api"
  location = var.gcp_region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0 # scale-to-zero — do not set > 0 without a reason
      max_instance_count = 4 # TODO: raise once real traffic patterns are known
    }

    containers {
      image = var.container_image

      ports {
        container_port = 8080
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      resources {
        # Keep CPU-during-requests-only (the default) unless background
        # threads/connection-pool keep-alive need "CPU always allocated" —
        # that flips the billing model, see reference.md.
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  # Migration Job must succeed before this service resource is applied,
  # so a bad migration never gets traffic routed to it. This is a
  # Terraform/OpenTofu-level ordering hint, not a substitute for the
  # deploy pipeline's own `gcloud run jobs execute --wait` gate (CI still
  # owns "did the job actually finish successfully" — see reference.md's
  # CD section) — `depends_on` here only prevents concurrent apply races.
  depends_on = [google_cloud_run_v2_job.migrate]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  # TODO: remove this if the service should not be publicly reachable
  # (e.g. it's only called from another internal service).
  name     = google_cloud_run_v2_service.api.name
  location = var.gcp_region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Migration Job — run-to-completion, fits the scale-to-zero philosophy
# (no idle cost, only billed for the seconds it actually runs). The CD
# pipeline must invoke this with `gcloud run jobs execute --wait` (or
# equivalent) BEFORE deploying a new service revision — see reference.md.
# Reuses the same app container image with an overridden entrypoint that
# runs the workspace's `migrator` binary (see backend/migrator/), not
# sqlx-cli directly, to avoid baking sqlx-cli into the runtime image.
resource "google_cloud_run_v2_job" "migrate" {
  name     = "${var.project_name}-migrate"
  location = var.gcp_region

  template {
    template {
      max_retries = 0 # a failed migration should fail the deploy, not silently retry
      containers {
        image   = var.container_image
        command = ["/app/migrator"]

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url_direct.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "${var.project_name}-${var.environment}-database-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.neon_connection_uri
}

resource "google_secret_manager_secret" "database_url_direct" {
  secret_id = "${var.project_name}-${var.environment}-database-url-direct"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url_direct" {
  secret      = google_secret_manager_secret.database_url_direct.id
  secret_data = local.neon_connection_uri_direct
}

output "cloud_run_url" {
  value = google_cloud_run_v2_service.api.uri
}

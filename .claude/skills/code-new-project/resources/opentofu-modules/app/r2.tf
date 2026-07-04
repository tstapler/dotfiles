# Cloudflare R2 — zero egress fees always, S3-API-compatible. See
# reference.md for why this beat S3 for unpredictable low-traffic reads.
# Schema verified against cloudflare/cloudflare v4.52.8.

resource "cloudflare_r2_bucket" "assets" {
  account_id = var.cloudflare_account_id
  name       = "${var.project_name}-${var.environment}-assets"
  location   = "ENAM" # TODO: match to your primary user base region
}

output "r2_bucket_name" {
  value = cloudflare_r2_bucket.assets.name
}

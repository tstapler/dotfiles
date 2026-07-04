# Neon serverless Postgres — one project shared across environments via
# BRANCHING, not one project per environment. True default scale-to-zero
# (5 min idle timeout), standard wire protocol, no proprietary lock-in.
# See reference.md for why branching beat separate-projects-per-env, and
# why Neon beat DynamoDB/Firestore/PlanetScale in the first place.
#
# Schema verified against kislerdm/neon provider v0.13.0 via
# `terraform providers schema -json` during scaffold authoring — unlike
# the RPC layer, this file's resource/attribute names are confirmed
# correct, not guessed.
#
# prod's neon_parent_branch_id should point at the Neon project's own
# default_branch_id (an output of the neon_project resource, defined
# wherever the Neon project itself is created — see the project-level
# setup note in the repo README, this module only manages branches
# WITHIN an existing project, not the project itself).

resource "neon_branch" "env" {
  project_id = var.neon_project_id
  parent_id  = var.neon_parent_branch_id
  name       = var.environment
}

resource "neon_endpoint" "env" {
  project_id = var.neon_project_id
  branch_id  = neon_branch.env.id
  type       = "read_write"
  # pooler_enabled/pooler_mode are provider-computed; Neon's pooler runs
  # PgBouncer in transaction mode by default, which does NOT support
  # session-level SQL PREPARE. sqlx should use protocol-level prepared
  # statements (works automatically with PgBouncer 1.22+) against the
  # pooled host below; migrations should use the DIRECT host instead —
  # see reference.md's migrations section.
}

resource "neon_role" "app" {
  project_id = var.neon_project_id
  branch_id  = neon_branch.env.id
  name       = "${var.project_name}_app"
}

resource "neon_database" "app" {
  project_id = var.neon_project_id
  branch_id  = neon_branch.env.id
  name       = var.project_name
  owner_name = neon_role.app.name
}

output "neon_branch_id" {
  value = neon_branch.env.id
}

# NOTE: `proxy_host` vs `host` mapping to pooled-vs-direct is inferred
# from field naming (proxy_host = PgBouncer-fronted, host = direct compute
# endpoint), matching Neon's typical `ep-xxx-pooler.region.aws.neon.tech`
# vs `ep-xxx.region.aws.neon.tech` hostname convention — the attribute
# NAMES are verified against the real provider schema (v0.13.0), but this
# specific semantic mapping was not independently confirmed against Neon's
# docs. Spot-check both hostnames against the Neon console's connection
# details for this branch before trusting this in production.
locals {
  # Pooled — for the app's runtime use (cloud_run.tf's service container).
  neon_connection_uri = "postgres://${neon_role.app.name}:${neon_role.app.password}@${neon_endpoint.env.proxy_host}/${neon_database.app.name}?sslmode=require"
  # Direct (non-pooled) — for migrations only (cloud_run.tf's migrate job).
  neon_connection_uri_direct = "postgres://${neon_role.app.name}:${neon_role.app.password}@${neon_endpoint.env.host}/${neon_database.app.name}?sslmode=require"
}

output "neon_connection_uri" {
  value     = local.neon_connection_uri
  sensitive = true
}

output "neon_connection_uri_direct" {
  value     = local.neon_connection_uri_direct
  sensitive = true
}

resource "google_service_account" "dbt_actions" {
  account_id   = local.service_account_id
  display_name = local.service_account_name
  project      = local.project_id
}

resource "google_project_iam_member" "bigquery_admin" {
  project = local.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.dbt_actions.email}"
}

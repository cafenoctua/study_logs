use crate::{error::AppError, models::ScanResult, scanner, AppState};
use axum::{extract::State, Json};
use std::path::Path;

pub async fn post_scan(State(state): State<AppState>) -> Result<Json<ScanResult>, AppError> {
    let result = scanner::scan_repository(
        &state.pool,
        Path::new(&state.session_dir),
        Path::new(&state.topics_file),
    )
    .await?;
    Ok(Json(result))
}

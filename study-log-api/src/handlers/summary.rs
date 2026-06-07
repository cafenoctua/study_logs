use crate::models::SummaryResponse;
use crate::{error::AppError, AppState};
use axum::{extract::State, Json};

pub async fn get_summary(State(state): State<AppState>) -> Result<Json<SummaryResponse>, AppError> {
    let total_sessions = sqlx::query_scalar!("SELECT COUNT(*) FROM sessions")
        .fetch_one(&state.pool)
        .await?;

    let total_topics = sqlx::query_scalar!("SELECT COUNT(*) FROM topics")
        .fetch_one(&state.pool)
        .await?;

    let completed_topics = sqlx::query_scalar!("SELECT COUNT(*) FROM topics WHERE completed = 1")
        .fetch_one(&state.pool)
        .await?;

    Ok(Json(SummaryResponse {
        total_sessions,
        total_topics,
        completed_topics,
    }))
}

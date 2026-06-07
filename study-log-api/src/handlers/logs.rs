use axum::{
    extract::{Path, Query, State},
    Json,
};

use crate::error::AppError;
use crate::models::{LogsQuery, SessionDetail, SessionRow, SessionSummary};
use crate::AppState;
use sqlx::QueryBuilder;

pub async fn get_by_id(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<SessionDetail>, AppError> {
    let row = sqlx::query_as!(SessionRow, "SELECT * FROM sessions WHERE id = ?", id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or(AppError::LogNotFound(id))?;
    Ok(Json(row.into()))
}

pub async fn list(
    State(state): State<AppState>,
    Query(params): Query<LogsQuery>,
) -> Result<Json<Vec<SessionSummary>>, AppError> {
    let mut qb = QueryBuilder::new("SELECT id, title, date FROM sessions WHERE 1=1");
    if let Some(d) = &params.date {
        qb.push(" AND date = ").push_bind(d);
    }
    if let Some(kw) = &params.keyword {
        qb.push(" AND content LIKE ").push_bind(format!("%{}%", kw));
    }
    let rows = qb
        .build_query_as::<SessionSummary>()
        .fetch_all(&state.pool)
        .await?;

    Ok(Json(rows))
}

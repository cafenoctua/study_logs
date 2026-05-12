use axum::{
    extract::{Path, State},
    Json,
};

use crate::error::AppError;
use crate::models::{SessionDetail, SessionRow};
use sqlx::SqlitePool;

pub async fn get_by_id(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<Json<SessionDetail>, AppError> {
    let row = sqlx::query_as!(SessionRow, "SELECT * FROM sessions WHERE id = ?", id)
        .fetch_optional(&pool)
        .await?
        .ok_or(AppError::LogNotFound(id))?;
    Ok(Json(row.into()))
}

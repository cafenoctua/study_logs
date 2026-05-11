use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;

#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("データベースエラー： {0}")]
    Database(#[from] sqlx::Error),
    #[error("ファイルが見つかりません：　{0}")]
    FileNotFound(String),
    #[error("ログが見つかりません： id={0}")]
    LogNotFound(i64),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let message = self.to_string();
        let status = match self {
            AppError::LogNotFound(_) => StatusCode::NOT_FOUND,
            AppError::FileNotFound(_) => StatusCode::NOT_FOUND,
            AppError::Database(_) => StatusCode::INTERNAL_SERVER_ERROR,
        };
        (status, Json(json!({ "error": message }))).into_response()
    }
}

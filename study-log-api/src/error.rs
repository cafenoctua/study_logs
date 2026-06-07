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
    #[error("マイグレーションエラー: {0}")]
    Migrate(#[from] sqlx::migrate::MigrateError),
    #[error("ファイルが見つかりません：　{0}")]
    FileNotFound(String),
    #[error("ログが見つかりません： id={0}")]
    LogNotFound(i64),
    #[error("IOエラー: {0}")]
    Io(#[from] std::io::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let message = self.to_string();
        let status = match self {
            AppError::LogNotFound(_) => StatusCode::NOT_FOUND,
            AppError::Migrate(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::FileNotFound(_) => StatusCode::NOT_FOUND,
            AppError::Database(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::Io(_) => StatusCode::INTERNAL_SERVER_ERROR,
        };
        (status, Json(json!({ "error": message }))).into_response()
    }
}

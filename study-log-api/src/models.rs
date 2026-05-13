use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, FromRow)]
pub struct SessionRow {
    pub id: i64,
    pub file_path: String,
    pub title: String,
    pub date: String,
    pub content: String,
    pub scanned_at: String,
}

#[derive(Debug, Serialize)]
pub struct SessionDetail {
    pub id: i64,
    pub title: String,
    pub date: String,
    pub content: String,
    pub scanned_at: String,
}

impl From<SessionRow> for SessionDetail {
    fn from(row: SessionRow) -> Self {
        Self {
            id: row.id,
            title: row.title,
            date: row.date,
            content: row.content,
            scanned_at: row.scanned_at,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct SessionSummary {
    pub id: i64,
    pub title: String,
    pub date: String,
}

#[derive(Debug, Deserialize)]
pub struct LogsQuery {
    pub date: Option<String>,
    pub keyword: Option<String>,
}

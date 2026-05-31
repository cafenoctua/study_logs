mod db;
mod error;
mod handlers;
mod models;
mod scanner;

use axum::{
    routing::{get, post},
    Router,
};
use sqlx::SqlitePool;

#[derive(Clone)]
struct AppState {
    pool: SqlitePool,
    session_dir: String,
    topics_file: String,
}

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();
    let database_url = std::env::var("DATABASE_URL").expect("DATABASE_URL not set");
    let pool = db::init_pool(&database_url).await.expect("DB init failed");

    let app_state = AppState {
        pool,
        session_dir: std::env::var("SESSION_DIR").expect("SESSION_DIR not set"),
        topics_file: std::env::var("TOPIC_FILE").expect("TOPICS_FILE not set"),
    };

    let app = Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/logs", get(handlers::logs::list))
        .route("/logs/{id}", get(handlers::logs::get_by_id))
        .route("/summary", get(handlers::summary::get_summary))
        .route("/scan", post(handlers::scan::post_scan))
        .with_state(app_state);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod test {
    use crate::handlers::logs::{get_by_id, list};
    use crate::handlers::summary::get_summary;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
        routing::get,
        Router,
    };
    use http_body_util::BodyExt;
    use sqlx::SqlitePool;
    use tower::ServiceExt;

    use crate::AppState;

    fn make_app(pool: SqlitePool) -> Router {
        let state = AppState {
            pool,
            session_dir: String::new(),
            topics_file: String::new(),
        };
        Router::new()
            .route("/logs", get(list))
            .route("/logs/{id}", get(get_by_id))
            .route("/summary", get(get_summary))
            .with_state(state)
    }

    #[sqlx::test]
    async fn test_get_logs_returns_all(pool: SqlitePool) {
        sqlx::query!(
            "INSERT INTO sessions (file_path, title, date, content, scanned_at)
             VALUES (?, ?, ?, ?, ?)",
            "/path/a.md",
            "タイトルA",
            "2026-05-31",
            "内容A",
            "2026-05-31T00:00:00+09:00"
        )
        .execute(&pool)
        .await
        .unwrap();

        let app = make_app(pool);

        let responce = app
            .oneshot(Request::builder().uri("/logs").body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(responce.status(), StatusCode::OK);
        let bytes = responce.into_body().collect().await.unwrap().to_bytes();
        let body: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(body.as_array().unwrap().len(), 1);
    }

    #[sqlx::test]
    async fn test_get_specific_date_logs(pool: SqlitePool) {
        sqlx::query!(
            "INSERT INTO sessions (file_path, title, date, content, scanned_at)
             VALUES (?, ?, ?, ?, ?)",
            "/path/a.md",
            "タイトルA",
            "2026-05-31",
            "内容A",
            "2026-05-31T00:00:00+09:00"
        )
        .execute(&pool)
        .await
        .unwrap();

        sqlx::query!(
            "INSERT INTO sessions (file_path, title, date, content, scanned_at)
             VALUES (?, ?, ?, ?, ?)",
            "/path/b.md",
            "タイトルA",
            "2026-06-01",
            "内容A",
            "2026-06-01T00:00:00+09:00"
        )
        .execute(&pool)
        .await
        .unwrap();

        let app = make_app(pool);

        let responce = app
            .oneshot(
                Request::builder()
                    .uri("/logs?date=2026-05-31")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(responce.status(), StatusCode::OK);
        let bytes = responce.into_body().collect().await.unwrap().to_bytes();
        let body: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(body.as_array().unwrap().len(), 1);
    }

    #[sqlx::test]
    async fn test_get_specific_keyword_logs(pool: SqlitePool) {
        sqlx::query!(
            "INSERT INTO sessions (file_path, title, date, content, scanned_at)
             VALUES (?, ?, ?, ?, ?)",
            "/path/a.md",
            "タイトルA",
            "2026-05-31",
            "内容A",
            "2026-05-31T00:00:00+09:00"
        )
        .execute(&pool)
        .await
        .unwrap();

        sqlx::query!(
            "INSERT INTO sessions (file_path, title, date, content, scanned_at)
             VALUES (?, ?, ?, ?, ?)",
            "/path/b.md",
            "タイトルB",
            "2026-06-01",
            "内容B",
            "2026-06-01T00:00:00+09:00"
        )
        .execute(&pool)
        .await
        .unwrap();

        let app = make_app(pool);

        let responce = app
            .oneshot(
                Request::builder()
                    .uri("/logs?keyword=内容A")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(responce.status(), StatusCode::OK);
        let bytes = responce.into_body().collect().await.unwrap().to_bytes();
        let body: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(body.as_array().unwrap().len(), 1);
    }

    #[sqlx::test]
    async fn test_get_logs_exists_id(pool: SqlitePool) {
        let result = sqlx::query!(
            "INSERT INTO sessions (file_path, title, date, content, scanned_at)
             VALUES (?, ?, ?, ?, ?)",
            "/path/a.md",
            "タイトルA",
            "2026-05-31",
            "内容A",
            "2026-05-31T00:00:00+09:00"
        )
        .execute(&pool)
        .await
        .unwrap();

        let app = make_app(pool);
        let id = result.last_insert_rowid();
        let uri = format!("/logs/{}", id);
        let responce = app
            .oneshot(Request::builder().uri(uri).body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(responce.status(), StatusCode::OK);
    }

    #[sqlx::test]
    async fn test_get_logs_not_exists_id(pool: SqlitePool) {
        let app = make_app(pool);

        let responce = app
            .oneshot(
                Request::builder()
                    .uri("/logs/100")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(responce.status(), StatusCode::NOT_FOUND);
    }
}

mod db;
mod error;
mod handlers;
mod models;

use axum::{routing::get, Router};

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();
    let database_url = std::env::var("DATABASE_URL").expect("DATABASE_URL not set");
    let pool = db::init_pool(&database_url).await.expect("DB init failed");

    let app = Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/logs", get(handlers::logs::list))
        .route("/logs/{id}", get(handlers::logs::get_by_id))
        .with_state(pool);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

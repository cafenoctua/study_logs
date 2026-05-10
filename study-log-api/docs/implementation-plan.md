# study-log-api 実装計画

## Context

Rustの習熟（特にasync/await）を目的として、study_logsリポジトリの学習記録をスキャン・提供するWebAPIを開発する。既存のdbt-impactプロジェクトで培ったトレイト・エラー処理・モジュール設計のパターンを活かしつつ、AxumとTokioで非同期処理を自然に学べる構成にする。

## 技術スタック

- **Webフレームワーク**: Axum 0.8
- **非同期ランタイム**: Tokio 1（features = ["full"]）
- **DB**: SQLite（SQLx 0.8）
- **エラー処理**: thiserror 2（dbt-impactと同パターン）
- **シリアライズ**: serde + serde_json
- **ログ**: tracing + tracing-subscriber

## プロジェクト構成

```
study_logs/
└── study-log-api/
    ├── Cargo.toml
    ├── .env                  # DATABASE_URL（gitignore）
    ├── migrations/
    │   └── 001_init.sql
    └── src/
        ├── main.rs           # Tokioランタイム起動 + Axumルーティング
        ├── error.rs          # AppError（thiserror + IntoResponse）
        ├── db.rs             # SqlitePool初期化 + マイグレーション
        ├── scanner.rs        # tokio::fsによるファイルスキャン
        ├── models.rs         # DB行 ↔ Rust構造体 ↔ APIレスポンス型
        └── handlers/
            ├── mod.rs
            ├── scan.rs       # POST /scan
            ├── summary.rs    # GET /summary
            └── logs.rs       # GET /logs, GET /logs/{id}
```

## データモデル

### migrations/001_init.sql

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT    NOT NULL UNIQUE,
    title       TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    scanned_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS topics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    source_file TEXT    NOT NULL,
    completed   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);
```

- `sessions` — `.claude/session/` 配下のMarkdownファイル1枚 = 1行
- `topics` — `Rust.md` のチェックボックス行（`- [x]`/`- [ ]`）を解析した結果

### Cargo.toml

```toml
[package]
name = "study-log-api"
version = "0.1.0"
edition = "2024"

[dependencies]
axum = "0.8"
tokio = { version = "1", features = ["full"] }
sqlx = { version = "0.8", features = ["sqlite", "runtime-tokio", "migrate"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "2"
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
```

## APIエンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| POST | /scan | リポジトリスキャンしてDBを更新 |
| GET | /summary | 学習サマリー（トピック一覧・進捗） |
| GET | /logs | セッションログ一覧（?date=&keyword=） |
| GET | /logs/{id} | 特定ログの詳細 |

## 実装順序（学習ステップ）

### Step 1: 骨格（最小Axumサーバー）
- `cargo new study-log-api` ← 完了済み
- `GET /health` だけ動く最小構成を `main.rs` に書く
- 学習ポイント: `#[tokio::main]`、`async fn`、`.await`の基礎

```rust
// main.rs の最初の形
use axum::{routing::get, Router};

#[tokio::main]
async fn main() {
    let app = Router::new().route("/health", get(|| async { "ok" }));
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
```

### Step 2: error.rs
- dbt-impact/src/error.rs を参照して `AppError` を定義
- `axum::response::IntoResponse` を実装（dbt-impactにはない追加点）
- 学習ポイント: 既知の `thiserror` を非同期Webの文脈へ応用

```rust
// error.rs
use axum::{http::StatusCode, response::{IntoResponse, Response}, Json};
use serde_json::json;

#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("データベースエラー: {0}")]
    Database(#[from] sqlx::Error),
    #[error("ファイルが見つかりません: {0}")]
    FileNotFound(String),
    #[error("ログが見つかりません: id={0}")]
    LogNotFound(i64),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            AppError::LogNotFound(_) => (StatusCode::NOT_FOUND, self.to_string()),
            AppError::FileNotFound(_) => (StatusCode::NOT_FOUND, self.to_string()),
            AppError::Database(_) => (StatusCode::INTERNAL_SERVER_ERROR, self.to_string()),
        };
        (status, Json(json!({ "error": message }))).into_response()
    }
}
```

### Step 3: db.rs + migrations/001_init.sql
- `SqlitePool::connect().await?` でプール初期化
- `sqlx::migrate!().run().await?` でマイグレーション自動実行
- `main.rs` で `State(pool)` としてRouterに注入
- 学習ポイント: `.await?` の組み合わせ、State依存注入

```rust
// db.rs
use sqlx::SqlitePool;
use crate::error::AppError;

pub async fn init_pool(database_url: &str) -> Result<SqlitePool, AppError> {
    let pool = SqlitePool::connect(database_url).await?;
    sqlx::migrate!("./migrations").run(&pool).await?;
    Ok(pool)
}
```

### Step 4: GET /logs/{id}（最も単純なハンドラ）
- `sqlx::query_as!` でDB取得、`Path` エクストラクタ
- 学習ポイント: Axumエクストラクタ、`query_as!`、`await?`チェーン

```rust
// handlers/logs.rs（一部）
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
```

### Step 5: GET /logs（クエリパラメータ付き）
- `Query<LogsQuery>` エクストラクタ、`Option` での条件分岐
- 学習ポイント: 動的SQLクエリ、`if let Some(kw)` パターン

### Step 6: GET /summary
- `sqlx::query_scalar!` で集計値取得
- 学習ポイント: 集計クエリ、複数クエリの `await?` 連続実行

### Step 7: POST /scan + scanner.rs（最も非同期らしいコード）
- `tokio::fs::read_dir().await?` + `while let Some(entry) = entries.next_entry().await?`
- Rust.mdのチェックボックス行をパース → topicsテーブルへupsert
- 学習ポイント: `tokio::fs` vs `std::fs`、非同期ループパターン

```rust
// scanner.rs（骨格）
pub async fn scan_repository(pool: &SqlitePool, repo_path: &Path) -> Result<ScanResult, AppError> {
    let mut entries = tokio::fs::read_dir(repo_path).await?;
    while let Some(entry) = entries.next_entry().await? {
        let content = tokio::fs::read_to_string(entry.path()).await?;
        upsert_session(pool, &entry, &content).await?;
    }
    Ok(ScanResult { /* ... */ })
}
```

## 参照すべき既存ファイル

- `../dbt-impact/src/error.rs` — AppErrorの雛形
- `../dbt-impact/src/main.rs` — モジュール構成の参考
- `../dbt-impact/src/manifest.rs` — モデル定義の参考
- `../rust_intro/Rust.md` — スキャン対象（チェックボックス行のフォーマット確認）

## 検証方法

```bash
# サーバー起動
cd study-log-api && cargo run

# ヘルスチェック
curl http://localhost:3000/health

# スキャン実行
curl -X POST http://localhost:3000/scan

# サマリー取得
curl http://localhost:3000/summary

# ログ一覧（キーワードフィルタ）
curl "http://localhost:3000/logs?keyword=async"

# 特定ログ取得
curl http://localhost:3000/logs/1

# テスト実行
cargo test
```

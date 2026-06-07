use crate::error::AppError;
use crate::models::ScanResult;
use sqlx::SqlitePool;
use std::path::Path;

pub async fn scan_repository(
    pool: &SqlitePool,
    session_dir: &Path,
    topics_file: &Path,
) -> Result<ScanResult, AppError> {
    let sessions_upserted = scan_sessions(pool, session_dir).await?;
    let topics_upserted = scan_topics(pool, topics_file).await?;
    Ok(ScanResult {
        sessions_upserted,
        topics_upserted,
    })
}

async fn scan_sessions(pool: &SqlitePool, dir: &Path) -> Result<i64, AppError> {
    let mut entries = tokio::fs::read_dir(dir).await?;
    let mut count = 0i64;

    while let Some(entry) = entries.next_entry().await? {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("md") {
            continue;
        }
        let content = tokio::fs::read_to_string(&path).await?;
        upsert_session(pool, &path, &content).await?;
        count += 1;
    }

    Ok(count)
}

async fn scan_topics(pool: &SqlitePool, file: &Path) -> Result<i64, AppError> {
    let content = tokio::fs::read_to_string(file).await?;
    let mut count = 0i64;

    for line in content.lines() {
        if let Some(name) = parse_checkbox(line) {
            let completed = line.starts_with("- [x]");
            upsert_topic(pool, name, completed, file).await?;
            count += 1;
        }
    }

    Ok(count)
}

fn parse_checkbox(line: &str) -> Option<&str> {
    // "- [x] トピック名"　か "- [ ] トピック名" にマッチ
    if let Some(rest) = line.strip_prefix("- [x] ") {
        Some(rest)
    } else if let Some(rest) = line.strip_prefix("- [ ] ") {
        Some(rest)
    } else {
        None
    }
}

async fn upsert_session(pool: &SqlitePool, path: &Path, content: &str) -> Result<(), AppError> {
    let file_path = path.to_string_lossy().to_string();
    let scanned_at = chrono::Local::now().to_rfc3339();
    let mut lines = content.lines();

    let title = lines
        .next()
        .unwrap_or("unknown")
        .trim_start_matches("# ")
        .to_string();

    let date = title.split(": ").nth(1).unwrap_or("unknown").to_string();

    sqlx::query!(
        "INSERT OR REPLACE INTO sessions (file_path, title, date, content, scanned_at)
         VALUES (?, ?, ?, ?, ?)",
        file_path,
        title,
        date,
        content,
        scanned_at
    )
    .execute(pool)
    .await?;

    Ok(())
}

async fn upsert_topic(
    pool: &SqlitePool,
    name: &str,
    completed: bool,
    source_file: &Path,
) -> Result<(), AppError> {
    let source_file_str = source_file.to_string_lossy().to_string();

    sqlx::query!(
        "INSERT OR REPLACE INTO topics (name, source_file, completed)
        VALUES (?, ?, ?)",
        name,
        source_file_str,
        completed
    )
    .execute(pool)
    .await?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // ユニットテスト（DBもファイルも不要）
    #[test]
    fn test_parse_checkbox_completed() {
        assert_eq!(parse_checkbox("- [x] async/await"), Some("async/await"));
    }

    #[test]
    fn test_parse_checkbox_incomplete() {
        assert_eq!(parse_checkbox("- [ ] async/await"), Some("async/await"));
    }

    #[test]
    fn test_parse_checkbox_non_checkbox() {
        assert_eq!(parse_checkbox("## セクション"), None);
    }

    #[test]
    fn test_parse_none_line() {
        assert_eq!(parse_checkbox(""), None);
    }

    #[test]
    fn test_parse_checkbox_with_url() {
        assert_eq!(
            parse_checkbox("- [x] https://example.com"),
            Some("https://example.com")
        );
    }
    // 統合テスト（インメモリDB使用）
    #[sqlx::test]
    async fn test_scan_topics_counts(pool: SqlitePool) {
        let file = tempfile::NamedTempFile::new().unwrap();
        std::fs::write(
            file.path(),
            "- [x] topic1\n- [ ] topic2\n- [x] topic3\n## header\n",
        )
        .unwrap();
        let count = scan_topics(&pool, file.path()).await.unwrap();
        assert_eq!(count, 3);
    }

    #[sqlx::test]
    async fn test_upsert_does_not_increase_count(pool: SqlitePool) {
        let file = tempfile::NamedTempFile::new().unwrap();
        std::fs::write(
            file.path(),
            "- [x] topic1\n- [ ] topic2\n- [x] topic3\n## header\n",
        )
        .unwrap();
        scan_topics(&pool, file.path()).await.unwrap();
        scan_topics(&pool, file.path()).await.unwrap();

        let count = sqlx::query_scalar!("SELECT COUNT(*) FROM topics")
            .fetch_one(&pool)
            .await
            .unwrap();
        assert_eq!(count, 3)
    }

    #[sqlx::test]
    async fn test_scan_topics_counts_skip_section(pool: SqlitePool) {
        let file = tempfile::NamedTempFile::new().unwrap();
        std::fs::write(
            file.path(),
            "- [x] topic1\n- [ ] topic2\n## header\n- [x] topic3\n",
        )
        .unwrap();

        scan_topics(&pool, file.path()).await.unwrap();

        let names: Vec<String> = sqlx::query_scalar!("SELECT name FROM topics")
            .fetch_all(&pool)
            .await
            .unwrap();
        assert!(!names.iter().any(|n| n.starts_with("##")));
    }

    #[sqlx::test]
    async fn test_scan_md_files(pool: SqlitePool) {
        let dir = tempfile::TempDir::new().unwrap();
        let md_path = dir.path().join("session1.md");
        std::fs::write(&md_path, "# Rust 学習ログ: 2026-05-31").unwrap();

        let txt_path = dir.path().join("session2.txt");
        std::fs::write(&txt_path, "# Rust 学習ログ: 2026-05-31").unwrap();

        scan_sessions(&pool, dir.path()).await.unwrap();

        let count = sqlx::query_scalar!("SELECT COUNT(*) FROM sessions")
            .fetch_one(&pool)
            .await
            .unwrap();
        assert_eq!(count, 1);
    }

    #[sqlx::test]
    async fn test_scan_session_return_title_date(pool: SqlitePool) {
        let dir = tempfile::TempDir::new().unwrap();
        let md_path = dir.path().join("session1.md");
        std::fs::write(&md_path, "# Rust 学習ログ: 2026-05-31").unwrap();

        scan_sessions(&pool, dir.path()).await.unwrap();

        let titles: Vec<String> = sqlx::query_scalar!("SELECT title FROM sessions")
            .fetch_all(&pool)
            .await
            .unwrap();

        let dates: Vec<String> = sqlx::query_scalar!("SELECT date FROM sessions")
            .fetch_all(&pool)
            .await
            .unwrap();

        assert_eq!(titles[0], "Rust 学習ログ: 2026-05-31");
        assert_eq!(dates[0], "2026-05-31");
    }

    #[sqlx::test]
    async fn test_upsert_session_does_not_increase_count(pool: SqlitePool) {
        let dir = tempfile::TempDir::new().unwrap();
        let md_path = dir.path().join("session1.md");
        std::fs::write(&md_path, "# Rust 学習ログ: 2026-05-31").unwrap();

        let txt_path = dir.path().join("session2.txt");
        std::fs::write(&txt_path, "# Rust 学習ログ: 2026-05-31").unwrap();

        scan_sessions(&pool, dir.path()).await.unwrap();
        scan_sessions(&pool, dir.path()).await.unwrap();

        let count = sqlx::query_scalar!("SELECT COUNT(*) FROM sessions")
            .fetch_one(&pool)
            .await
            .unwrap();
        assert_eq!(count, 1);
    }
}

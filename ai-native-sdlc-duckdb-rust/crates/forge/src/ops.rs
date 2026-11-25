//! 計測用の ops スキーマ(warehouse/prod.duckdb 内)への記録と、読み取り専用クエリ。

use std::path::{Path, PathBuf};

use anyhow::{bail, Result};
use duckdb::types::Value as DValue;

use crate::runner::{utc_now, RunResults};
use crate::warehouse::Db;

pub const OPS_TABLES_SQL: &str = include_str!("../../../monitoring/sql/ops_tables.sql");

/// 本番 DuckDB ファイルの場所(環境変数 PROD_DB で上書き可)。
pub fn prod_db_path(root: &Path) -> PathBuf {
    std::env::var("PROD_DB")
        .map(PathBuf::from)
        .unwrap_or_else(|_| root.join("warehouse").join("prod.duckdb"))
}

/// ops スキーマとテーブルを作る(冪等)。
pub fn init(db: &Db) -> Result<()> {
    db.execute(OPS_TABLES_SQL)
}

fn text(s: &str) -> DValue {
    DValue::Text(s.to_string())
}

fn opt_text(s: Option<&str>) -> DValue {
    s.map(text).unwrap_or(DValue::Null)
}

/// run_results.json を ops.run_results に保存する。
pub fn upload_results(
    db: &Db,
    results: &RunResults,
    target: &str,
    git_sha: Option<&str>,
) -> Result<usize> {
    let mut n = 0;
    for r in &results.results {
        n += db.execute_with(
            "insert into ops.run_results values (?, ?, ?, ?, ?, ?, cast(? as timestamp))",
            vec![
                text(&results.invocation_id),
                text(target),
                opt_text(git_sha),
                text(&r.unique_id),
                text(r.status.as_str()),
                DValue::Double(r.execution_time_s),
                text(&results.generated_at),
            ],
        )?;
    }
    Ok(n)
}

pub fn record_deployment(db: &Db, git_sha: &str, approver: &str, status: &str) -> Result<()> {
    if !matches!(status, "success" | "failed" | "rolled_back") {
        bail!("status は success / failed / rolled_back のいずれかです");
    }
    db.execute_with(
        "insert into ops.deployments values (cast(? as timestamp), ?, ?, ?)",
        vec![
            text(&utc_now()),
            text(git_sha),
            text(approver),
            text(status),
        ],
    )?;
    Ok(())
}

pub fn record_ci_run(db: &Db, git_sha: &str, pr: &str, attempt: i32, status: &str) -> Result<()> {
    if !matches!(status, "success" | "failure") {
        bail!("status は success / failure のどちらかです");
    }
    db.execute_with(
        "insert into ops.ci_runs values (cast(? as timestamp), ?, ?, ?, ?)",
        vec![
            text(&utc_now()),
            text(git_sha),
            text(pr),
            DValue::Int(attempt),
            text(status),
        ],
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runner::{NodeResult, Status};

    #[test]
    fn records_into_ops() {
        let db = Db::in_memory().unwrap();
        init(&db).unwrap();
        init(&db).unwrap(); // 冪等
        let rr = RunResults {
            invocation_id: "inv".into(),
            generated_at: utc_now(),
            command: "build".into(),
            target: "prod".into(),
            elapsed_s: 1.0,
            results: vec![NodeResult {
                unique_id: "model.p.m".into(),
                resource_type: "model".into(),
                name: "m".into(),
                status: Status::Success,
                execution_time_s: 0.2,
                message: None,
                failures: None,
            }],
        };
        assert_eq!(upload_results(&db, &rr, "prod", Some("abc")).unwrap(), 1);
        record_deployment(&db, "abc", "taro", "success").unwrap();
        record_ci_run(&db, "abc", "12", 1, "failure").unwrap();
        assert!(record_deployment(&db, "abc", "taro", "ok").is_err());
        let r = db
            .query("select count(*) as n from ops.deployments")
            .unwrap();
        assert_eq!(r.get_f64(0, "n"), Some(1.0));
        let r = db
            .query("select execution_seconds from ops.run_results")
            .unwrap();
        assert_eq!(r.get_f64(0, "execution_seconds"), Some(0.2));
    }
}

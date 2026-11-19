//! DuckDB への接続(duckdb クレート。DuckDB 本体を同梱してビルドする)。

use std::path::Path;

use anyhow::{Context, Result};
use duckdb::types::{TimeUnit, Value as DValue};
use duckdb::{AccessMode, Config, Connection};
use serde_json::Value;

use crate::config::{catalog_of, Target};
use crate::project::Relation;

/// クエリ結果。値は表示しやすい JSON(数値・真偽値はそのまま、時刻などは文字列)。
#[derive(Debug, Clone, Default, PartialEq)]
pub struct QueryResult {
    pub columns: Vec<String>,
    pub rows: Vec<Vec<Value>>,
}

impl QueryResult {
    pub fn get(&self, row: usize, column: &str) -> Option<&Value> {
        let idx = self.columns.iter().position(|c| c == column)?;
        self.rows.get(row)?.get(idx)
    }

    pub fn get_f64(&self, row: usize, column: &str) -> Option<f64> {
        match self.get(row, column)? {
            Value::Number(n) => n.as_f64(),
            Value::String(s) => s.parse().ok(),
            _ => None,
        }
    }

    pub fn get_str(&self, row: usize, column: &str) -> Option<String> {
        match self.get(row, column)? {
            Value::Null => None,
            Value::String(s) => Some(s.clone()),
            other => Some(other.to_string()),
        }
    }

    pub fn records(&self) -> Vec<serde_json::Map<String, Value>> {
        self.rows
            .iter()
            .map(|r| {
                self.columns
                    .iter()
                    .cloned()
                    .zip(r.iter().cloned())
                    .collect()
            })
            .collect()
    }

    /// 端末向けの簡易な表。
    pub fn to_table(&self) -> String {
        let cell = |v: &Value| match v {
            Value::Null => "NULL".to_string(),
            Value::String(s) => s.clone(),
            other => other.to_string(),
        };
        let cells: Vec<Vec<String>> = self
            .rows
            .iter()
            .map(|r| r.iter().map(cell).collect())
            .collect();
        let widths: Vec<usize> = self
            .columns
            .iter()
            .enumerate()
            .map(|(i, c)| {
                cells
                    .iter()
                    .map(|r| r[i].chars().count())
                    .chain([c.chars().count()])
                    .max()
                    .unwrap_or(0)
            })
            .collect();
        let line = |vals: &[String]| {
            vals.iter()
                .zip(&widths)
                .map(|(v, w)| format!("{v:<w$}", w = *w))
                .collect::<Vec<_>>()
                .join(" | ")
        };
        let mut out = line(&self.columns);
        out.push('\n');
        out.push_str(
            &widths
                .iter()
                .map(|w| "-".repeat(*w))
                .collect::<Vec<_>>()
                .join("-+-"),
        );
        for r in &cells {
            out.push('\n');
            out.push_str(&line(r));
        }
        out
    }
}

/// SQL 文字列リテラル('' でエスケープ)。
pub fn quote_str(s: &str) -> String {
    format!("'{}'", s.replace('\'', "''"))
}

pub struct Db {
    conn: Connection,
    pub catalog: String,
}

impl Db {
    /// ファイルを開く。read_only なら書き込みは DuckDB が拒否する。
    pub fn open_path(path: &Path, read_only: bool) -> Result<Self> {
        if !read_only {
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent)?;
            }
        }
        let mode = if read_only {
            AccessMode::ReadOnly
        } else {
            AccessMode::ReadWrite
        };
        let conn = Connection::open_with_flags(path, Config::default().access_mode(mode)?)
            .with_context(|| {
                format!(
                    "{} を開けません(他のプロセスが使用中かもしれません)",
                    path.display()
                )
            })?;
        Ok(Self {
            conn,
            catalog: catalog_of(path),
        })
    }

    /// ターゲットを開き、attach を付け、スキーマを用意する。
    pub fn open_target(target: &Target, schemas: &[&str]) -> Result<Self> {
        let db = Self::open_path(&target.path, false)?;
        for a in &target.attach {
            if !a.path.exists() {
                eprintln!(
                    "注意: attach 先 {} がありません(defer はできません)",
                    a.path.display()
                );
                continue;
            }
            let opt = if a.read_only { " (READ_ONLY)" } else { "" };
            db.execute(&format!(
                "attach {} as {}{opt}",
                quote_str(&a.path.to_string_lossy()),
                a.alias
            ))?;
        }
        for s in schemas {
            db.execute(&format!("create schema if not exists {}.{s}", db.catalog))?;
        }
        Ok(db)
    }

    pub fn in_memory() -> Result<Self> {
        Ok(Self {
            conn: Connection::open_in_memory()?,
            catalog: "memory".into(),
        })
    }

    /// 複数文をそのまま実行する(結果は捨てる)。
    pub fn execute(&self, sql: &str) -> Result<()> {
        self.conn
            .execute_batch(sql)
            .with_context(|| format!("SQL の実行に失敗:\n{}", preview(sql)))
    }

    /// 1文を実行し、影響行数を返す。
    pub fn execute_count(&self, sql: &str) -> Result<usize> {
        self.conn
            .execute(sql, [])
            .with_context(|| format!("SQL の実行に失敗:\n{}", preview(sql)))
    }

    /// プレースホルダ(`?`)付きの1文を実行する。
    pub fn execute_with(&self, sql: &str, params: Vec<DValue>) -> Result<usize> {
        self.conn
            .execute(sql, duckdb::params_from_iter(params))
            .with_context(|| format!("SQL の実行に失敗:\n{}", preview(sql)))
    }

    /// 1文(SELECT など)を実行して結果を返す。
    pub fn query(&self, sql: &str) -> Result<QueryResult> {
        let mut stmt = self
            .conn
            .prepare(sql)
            .with_context(|| format!("SQL の解析に失敗:\n{}", preview(sql)))?;
        let mut rows = stmt.query([])?;
        let columns: Vec<String> = rows.as_ref().map(|s| s.column_names()).unwrap_or_default();
        let n = columns.len();
        let mut out = Vec::new();
        while let Some(row) = rows.next()? {
            let mut r = Vec::with_capacity(n);
            for i in 0..n {
                r.push(to_json(row.get::<_, DValue>(i)?));
            }
            out.push(r);
        }
        Ok(QueryResult { columns, rows: out })
    }

    /// `BASE TABLE` / `VIEW`。なければ None。
    pub fn relation_kind(&self, rel: &Relation) -> Result<Option<String>> {
        let r = self.query(&format!(
            "select table_type from information_schema.tables \
             where table_catalog = {} and table_schema = {} and table_name = {}",
            quote_str(&rel.database),
            quote_str(&rel.schema),
            quote_str(&rel.name)
        ))?;
        Ok(r.get_str(0, "table_type"))
    }

    pub fn columns(&self, rel: &Relation) -> Result<Vec<String>> {
        let r = self.query(&format!(
            "select column_name from information_schema.columns \
             where table_catalog = {} and table_schema = {} and table_name = {} order by ordinal_position",
            quote_str(&rel.database),
            quote_str(&rel.schema),
            quote_str(&rel.name)
        ))?;
        Ok((0..r.rows.len())
            .filter_map(|i| r.get_str(i, "column_name"))
            .collect())
    }
}

fn preview(sql: &str) -> String {
    let s: String = sql.chars().take(800).collect();
    if sql.chars().count() > 800 {
        format!("{s}\n…")
    } else {
        s
    }
}

fn ts(unit: TimeUnit, v: i64) -> String {
    let micros = match unit {
        TimeUnit::Second => v * 1_000_000,
        TimeUnit::Millisecond => v * 1_000,
        TimeUnit::Microsecond => v,
        TimeUnit::Nanosecond => v / 1_000,
    };
    chrono::DateTime::from_timestamp_micros(micros)
        .map(|d| d.naive_utc().format("%Y-%m-%d %H:%M:%S%.f").to_string())
        .unwrap_or_else(|| v.to_string())
}

fn to_json(v: DValue) -> Value {
    use serde_json::json;
    match v {
        DValue::Null => Value::Null,
        DValue::Boolean(b) => json!(b),
        DValue::TinyInt(i) => json!(i),
        DValue::SmallInt(i) => json!(i),
        DValue::Int(i) => json!(i),
        DValue::BigInt(i) => json!(i),
        DValue::HugeInt(i) => json!(i.to_string()),
        DValue::UTinyInt(i) => json!(i),
        DValue::USmallInt(i) => json!(i),
        DValue::UInt(i) => json!(i),
        DValue::UBigInt(i) => json!(i),
        DValue::Float(f) => json!(f),
        DValue::Double(f) => json!(f),
        DValue::Decimal(d) => json!(d.to_string()),
        DValue::Text(s) => json!(s),
        DValue::Timestamp(u, v) => json!(ts(u, v)),
        DValue::Date32(d) => json!(chrono::NaiveDate::from_num_days_from_ce_opt(d + 719_163)
            .map(|d| d.to_string())
            .unwrap_or_else(|| d.to_string())),
        other => json!(format!("{other:?}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn query_converts_types() {
        let db = Db::in_memory().unwrap();
        let r = db
            .query(
                "select 1 as i, 1.5::double as d, 'x' as s, null as n, date '2026-11-16' as dt, \
                    timestamp '2026-11-16 09:00:00' as ts, 12.30::decimal(10,2) as dec",
            )
            .unwrap();
        assert_eq!(r.get_f64(0, "i"), Some(1.0));
        assert_eq!(r.get_f64(0, "d"), Some(1.5));
        assert_eq!(r.get_str(0, "s").as_deref(), Some("x"));
        assert_eq!(r.get_str(0, "n"), None);
        assert_eq!(r.get_str(0, "dt").as_deref(), Some("2026-11-16"));
        assert_eq!(r.get_str(0, "ts").as_deref(), Some("2026-11-16 09:00:00"));
        assert_eq!(r.get_f64(0, "dec"), Some(12.3));
        assert!(r.to_table().contains("2026-11-16"));
    }

    #[test]
    fn read_only_rejects_writes() {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("w.duckdb");
        Db::open_path(&p, false)
            .unwrap()
            .execute("create table t(a int)")
            .unwrap();
        let ro = Db::open_path(&p, true).unwrap();
        assert!(ro.execute("insert into t values (1)").is_err());
        assert_eq!(
            ro.query("select count(*) as n from t")
                .unwrap()
                .get_f64(0, "n"),
            Some(0.0)
        );
    }
}

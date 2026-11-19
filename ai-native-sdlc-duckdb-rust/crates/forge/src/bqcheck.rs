//! BigQuery 互換チェック(接続なし)。
//!
//! 各モデルを描画し、sqlparser の BigQuery 方言で構文解析したうえで、
//! DuckDB では通るが BigQuery では通らない書き方を検出する。
//! dbt v2 の `--static-analysis strict` と違い **型の解析はしない**(構文と既知の書き方のみ)。

use std::collections::{BTreeSet, HashMap};
use std::ops::ControlFlow;

use anyhow::Result;
use sqlparser::ast::{visit_expressions, CastKind, Expr, FunctionArguments};
use sqlparser::dialect::{BigQueryDialect, DuckDbDialect};
use sqlparser::parser::Parser;

use crate::config::Target;
use crate::project::{NodeKind, Project};
use crate::state;

#[derive(Debug, Clone, PartialEq)]
pub struct Finding {
    pub model: String,
    pub message: String,
}

/// BigQuery に無い型名(CAST 先)と代わりの型。
const TYPE_HINTS: &[(&str, &str)] = &[
    ("VARCHAR", "STRING"),
    ("TEXT", "STRING"),
    ("DOUBLE", "FLOAT64"),
    ("REAL", "FLOAT64"),
    ("FLOAT", "FLOAT64"),
    ("HUGEINT", "BIGNUMERIC"),
    ("UBIGINT", "INT64 / NUMERIC"),
];

/// SQL 1つを調べる。
pub fn check_sql(sql: &str) -> Vec<String> {
    let mut found = BTreeSet::new();
    // BigQuery 方言で解析できなければ、その旨を記録したうえで DuckDB 方言で読み直し、原因の書き方を探す
    let stmts = match Parser::parse_sql(&BigQueryDialect {}, sql) {
        Ok(s) => s,
        Err(e) => {
            found.insert(format!("BigQuery 方言として解析できません: {e}"));
            match Parser::parse_sql(&DuckDbDialect {}, sql) {
                Ok(s) => s,
                Err(_) => return found.into_iter().collect(),
            }
        }
    };
    let _ = visit_expressions(&stmts, |expr| {
        match expr {
            Expr::Function(f) => {
                let name = f.name.to_string().to_ascii_lowercase();
                if f.filter.is_some() {
                    found.insert(format!(
                        "{name}(...) filter (where ...) は BigQuery にありません → countif / sum(if(...)) などに書き換え"
                    ));
                }
                if matches!(
                    name.as_str(),
                    "date_trunc" | "timestamp_trunc" | "datetime_trunc"
                ) {
                    if let FunctionArguments::List(list) = &f.args {
                        if list
                            .args
                            .first()
                            .is_some_and(|a| a.to_string().starts_with('\''))
                        {
                            found.insert(format!(
                                "{name}('part', x) は DuckDB の引数順です → BigQuery は {name}(x, part)"
                            ));
                        }
                    }
                }
            }
            Expr::Cast {
                kind, data_type, ..
            } => {
                if *kind == CastKind::DoubleColon {
                    found.insert(
                        "`x::type` の型変換は BigQuery にありません → cast(x as type)".into(),
                    );
                }
                let t = data_type.to_string().to_ascii_uppercase();
                let base = t.split('(').next().unwrap_or("").trim();
                if let Some((_, alt)) = TYPE_HINTS.iter().find(|(d, _)| *d == base) {
                    found.insert(format!("型 {base} は BigQuery にありません → {alt}"));
                }
            }
            _ => {}
        }
        ControlFlow::<()>::Continue(())
    });
    found.into_iter().collect()
}

/// 全モデルを調べる(seed は対象外)。
pub fn check_project(project: &Project) -> Result<Vec<Finding>> {
    let target = Target {
        name: "bq_compat".into(),
        path: "bq_compat".into(),
        schema: "analytics".into(),
        attach: vec![],
    };
    let all = project.nodes.keys().cloned().collect();
    let rels: HashMap<_, _> = state::resolve_relations(project, &target, &all, None);
    let mut out = Vec::new();
    for (name, node) in &project.nodes {
        if node.kind == NodeKind::Seed {
            continue;
        }
        // incremental の分岐も両方調べる
        for inc in [false, true] {
            let sql = project.compile(name, &target, &rels, inc)?;
            for message in check_sql(&sql) {
                let f = Finding {
                    model: name.clone(),
                    message,
                };
                if !out.contains(&f) {
                    out.push(f);
                }
            }
        }
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_portable_sql() {
        let sql = "select customer_id, count(*) as n, cast(amount as decimal(12, 2)) as a, \
                   date_trunc(ordered_at, week) as w \
                   from p.analytics.fct_orders where is_revenue group by 1, 3, 4";
        assert!(check_sql(sql).is_empty(), "{:?}", check_sql(sql));
    }

    #[test]
    fn flags_duckdb_isms() {
        let f = check_sql(
            "select count(*) filter (where ok) as n, date_trunc('week', ts) as w, \
                           x::int as i, cast(y as varchar) as s from t",
        );
        let all = f.join("\n");
        assert!(all.contains("filter (where"), "{all}");
        assert!(all.contains("引数順"), "{all}");
        assert!(all.contains("x::type"), "{all}");
        assert!(all.contains("VARCHAR"), "{all}");
    }
}

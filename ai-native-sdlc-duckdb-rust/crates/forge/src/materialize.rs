//! マテリアライズ(view / table / incremental / seed)とデータテストの SQL 生成。純粋関数のみ。

use std::path::Path;

use crate::project::{ModelConfig, Relation};
use crate::schema::DataTest;
use crate::warehouse::quote_str;

pub fn create_view(rel: &Relation, sql: &str) -> String {
    format!("create or replace view {rel} as\n{sql}")
}

pub fn create_table(rel: &Relation, sql: &str) -> String {
    format!("create or replace table {rel} as\n{sql}")
}

pub fn drop_relation(rel: &Relation, kind: &str) -> String {
    let what = if kind.eq_ignore_ascii_case("VIEW") {
        "view"
    } else {
        "table"
    };
    format!("drop {what} if exists {rel}")
}

/// CSV をそのままテーブルにする(型は DuckDB の自動判定)。
pub fn load_seed(rel: &Relation, csv: &Path) -> String {
    format!(
        "create or replace table {rel} as\nselect * from read_csv({}, header = true, auto_detect = true)",
        quote_str(&csv.to_string_lossy())
    )
}

/// 既存テーブルへの増分反映。unique_key があれば delete+insert、なければ追記。
/// 1トランザクションで実行するので、途中で失敗しても既存データは残る。
pub fn incremental(rel: &Relation, cfg: &ModelConfig, sql: &str, columns: &[String]) -> String {
    let tmp = format!("__forge_tmp_{}", rel.name);
    let cols = columns.join(", ");
    let keys = cfg.unique_keys();
    let mut s = format!("begin transaction;\ncreate or replace temp table {tmp} as\n{sql};\n");
    if !keys.is_empty() {
        let cond = keys
            .iter()
            .map(|k| format!("{rel}.{k} = {tmp}.{k}"))
            .collect::<Vec<_>>()
            .join(" and ");
        s.push_str(&format!("delete from {rel} using {tmp} where {cond};\n"));
    }
    s.push_str(&format!(
        "insert into {rel} ({cols}) select {cols} from {tmp};\n"
    ));
    s.push_str(&format!("drop table {tmp};\ncommit;"));
    s
}

/// 失敗行の件数を `failures` 列で返す SQL。
pub fn test_sql(test: &DataTest, rel: &Relation, column: &str, to: Option<&Relation>) -> String {
    let inner = match test {
        DataTest::Unique => format!(
            "select {column} from {rel} where {column} is not null group by {column} having count(*) > 1"
        ),
        DataTest::NotNull => format!("select {column} from {rel} where {column} is null"),
        DataTest::AcceptedValues { values } => {
            let list = values.iter().map(|v| quote_str(v)).collect::<Vec<_>>().join(", ");
            format!("select {column} from {rel} where cast({column} as varchar) not in ({list})")
        }
        DataTest::Relationships { field, .. } => {
            let to = to.expect("relationships には参照先が必要");
            format!(
                "select c.{column} from {rel} as c left join {to} as p on c.{column} = p.{field} \
                 where c.{column} is not null and p.{field} is null"
            )
        }
    };
    format!("select count(*) as failures from (\n{inner}\n)")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::Materialized;
    use crate::project::OneOrMany;

    fn rel() -> Relation {
        Relation {
            database: "prod".into(),
            schema: "analytics".into(),
            name: "m".into(),
        }
    }

    #[test]
    fn ddl() {
        assert_eq!(
            create_table(&rel(), "select 1"),
            "create or replace table prod.analytics.m as\nselect 1"
        );
        assert!(load_seed(&rel(), Path::new("/x/it's.csv")).contains("read_csv('/x/it''s.csv'"));
    }

    #[test]
    fn delete_insert_by_key() {
        let cfg = ModelConfig {
            materialized: Materialized::Incremental,
            unique_key: Some(OneOrMany::One("id".into())),
            tags: vec![],
        };
        let s = incremental(&rel(), &cfg, "select 1 as id", &["id".into(), "v".into()]);
        assert!(s.contains("delete from prod.analytics.m using __forge_tmp_m where prod.analytics.m.id = __forge_tmp_m.id;"));
        assert!(s.contains("insert into prod.analytics.m (id, v) select id, v from __forge_tmp_m;"));
        assert!(s.starts_with("begin transaction;") && s.ends_with("commit;"));
    }

    #[test]
    fn test_sql_escapes_values() {
        let s = test_sql(
            &DataTest::AcceptedValues {
                values: vec!["a".into(), "it's".into()],
            },
            &rel(),
            "s",
            None,
        );
        assert!(s.contains("not in ('a', 'it''s')"));
    }
}

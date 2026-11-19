//! models/ 配下の `*.yml`(ソース定義・モデルの説明・データテスト)。
//! dbt の schema.yml と同じ書き方の、よく使う部分だけに対応する。

use std::collections::BTreeMap;

use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Default, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SchemaFile {
    #[allow(dead_code)]
    pub version: Option<u32>,
    #[serde(default)]
    pub sources: Vec<SourceDef>,
    #[serde(default)]
    pub models: Vec<ModelDoc>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct SourceDef {
    pub name: String,
    /// BigQuery のプロジェクト。省略時はターゲットと同じ
    pub database: Option<String>,
    /// BigQuery のデータセット。省略時は name
    pub schema: Option<String>,
    pub loaded_at_field: Option<String>,
    pub freshness: Option<Freshness>,
    pub tables: Vec<SourceTable>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct SourceTable {
    pub name: String,
    pub identifier: Option<String>,
    pub loaded_at_field: Option<String>,
    pub freshness: Option<Freshness>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Freshness {
    pub warn_after: Option<Period>,
    pub error_after: Option<Period>,
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Period {
    pub count: u64,
    pub period: PeriodUnit,
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum PeriodUnit {
    Minute,
    Hour,
    Day,
}

impl Period {
    pub fn seconds(&self) -> u64 {
        self.count
            * match self.period {
                PeriodUnit::Minute => 60,
                PeriodUnit::Hour => 3600,
                PeriodUnit::Day => 86400,
            }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct ModelDoc {
    pub name: String,
    pub description: Option<String>,
    #[serde(default)]
    pub columns: Vec<ColumnDoc>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct ColumnDoc {
    pub name: String,
    pub description: Option<String>,
    #[serde(default, alias = "data_tests")]
    pub tests: Vec<TestSpec>,
}

/// YAML 上の書き方: `unique` / `{accepted_values: {values: [...]}}`
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(untagged)]
pub enum TestSpec {
    Name(String),
    WithArgs(BTreeMap<String, serde_yaml::Value>),
}

#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum DataTest {
    Unique,
    NotNull,
    AcceptedValues {
        values: Vec<String>,
    },
    /// `to` は参照先モデル名(`ref('x')` の x)
    Relationships {
        to: String,
        field: String,
    },
}

impl DataTest {
    pub fn kind_name(&self) -> &'static str {
        match self {
            DataTest::Unique => "unique",
            DataTest::NotNull => "not_null",
            DataTest::AcceptedValues { .. } => "accepted_values",
            DataTest::Relationships { .. } => "relationships",
        }
    }
}

impl TestSpec {
    pub fn to_test(&self) -> Result<DataTest> {
        match self {
            TestSpec::Name(n) => match n.as_str() {
                "unique" => Ok(DataTest::Unique),
                "not_null" => Ok(DataTest::NotNull),
                other => bail!(
                    "未対応のテスト: {other}(unique / not_null / accepted_values / relationships)"
                ),
            },
            TestSpec::WithArgs(m) => {
                let Some((name, args)) = m.iter().next().filter(|_| m.len() == 1) else {
                    bail!("テストの指定は1つのキーにしてください: {m:?}");
                };
                // dbt v2 形式の `arguments:` の入れ子にも対応する
                let args = args.get("arguments").unwrap_or(args);
                match name.as_str() {
                    "unique" => Ok(DataTest::Unique),
                    "not_null" => Ok(DataTest::NotNull),
                    "accepted_values" => {
                        let values = args
                            .get("values")
                            .and_then(|v| v.as_sequence())
                            .ok_or_else(|| {
                                anyhow::anyhow!("accepted_values には values が必要です")
                            })?
                            .iter()
                            .map(yaml_scalar)
                            .collect::<Result<Vec<_>>>()?;
                        Ok(DataTest::AcceptedValues { values })
                    }
                    "relationships" => {
                        let to = args.get("to").and_then(|v| v.as_str()).unwrap_or_default();
                        let field = args
                            .get("field")
                            .and_then(|v| v.as_str())
                            .unwrap_or_default();
                        if to.is_empty() || field.is_empty() {
                            bail!("relationships には to と field が必要です");
                        }
                        Ok(DataTest::Relationships {
                            to: parse_ref_expr(to)?,
                            field: field.into(),
                        })
                    }
                    other => bail!("未対応のテスト: {other}"),
                }
            }
        }
    }
}

fn yaml_scalar(v: &serde_yaml::Value) -> Result<String> {
    Ok(match v {
        serde_yaml::Value::String(s) => s.clone(),
        serde_yaml::Value::Number(n) => n.to_string(),
        serde_yaml::Value::Bool(b) => b.to_string(),
        other => bail!("accepted_values の値はスカラーにしてください: {other:?}"),
    })
}

/// `ref('dim_customers')` / `ref("dim_customers")` / `dim_customers` からモデル名を取り出す。
pub fn parse_ref_expr(s: &str) -> Result<String> {
    let s = s.trim();
    let inner = match s.strip_prefix("ref(").and_then(|r| r.strip_suffix(')')) {
        Some(i) => i.trim().trim_matches(|c| c == '\'' || c == '"'),
        None => s,
    };
    if inner.is_empty() || !inner.chars().all(|c| c.is_ascii_alphanumeric() || c == '_') {
        bail!("参照先モデル名が不正です: {s}");
    }
    Ok(inner.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_schema_file() {
        let y = r#"
version: 2
sources:
  - name: shop
    schema: raw_shop
    loaded_at_field: _loaded_at
    freshness:
      warn_after: {count: 6, period: hour}
    tables:
      - name: orders
models:
  - name: m
    columns:
      - name: id
        tests: [unique, not_null]
      - name: status
        data_tests:
          - accepted_values:
              values: [a, b, 1]
      - name: customer_id
        tests:
          - relationships:
              arguments:
                to: ref('dim_customers')
                field: customer_id
"#;
        let f: SchemaFile = serde_yaml::from_str(y).unwrap();
        assert_eq!(
            f.sources[0]
                .freshness
                .as_ref()
                .unwrap()
                .warn_after
                .unwrap()
                .seconds(),
            6 * 3600
        );
        let tests: Vec<DataTest> = f.models[0]
            .columns
            .iter()
            .flat_map(|c| c.tests.iter().map(|t| t.to_test().unwrap()))
            .collect();
        assert_eq!(
            tests,
            vec![
                DataTest::Unique,
                DataTest::NotNull,
                DataTest::AcceptedValues {
                    values: vec!["a".into(), "b".into(), "1".into()]
                },
                DataTest::Relationships {
                    to: "dim_customers".into(),
                    field: "customer_id".into()
                },
            ]
        );
    }

    #[test]
    fn rejects_unknown_tests() {
        assert!(TestSpec::Name("expect_magic".into()).to_test().is_err());
        assert!(parse_ref_expr("ref('a b')").is_err());
    }
}

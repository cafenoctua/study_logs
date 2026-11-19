//! `forge_project.toml`(プロジェクト設定)と `profiles.toml`(接続先)の読み込み。

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use anyhow::{anyhow, bail, Context, Result};
use serde::{Deserialize, Serialize};

pub const PROJECT_FILE: &str = "forge_project.toml";
pub const PROFILES_FILE: &str = "profiles.toml";

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct ProjectConfig {
    pub name: String,
    pub profile: String,
    #[serde(default = "default_model_paths")]
    pub model_paths: Vec<String>,
    #[serde(default = "default_seed_paths")]
    pub seed_paths: Vec<String>,
    #[serde(default = "default_target_path")]
    pub target_path: String,
    /// モデルディレクトリ(`models/` 直下のフォルダ名)ごとの既定設定
    #[serde(default)]
    pub models: BTreeMap<String, ModelDefaults>,
    #[serde(default)]
    pub seeds: SeedConfig,
}

fn default_model_paths() -> Vec<String> {
    vec!["models".into()]
}
fn default_seed_paths() -> Vec<String> {
    vec!["seeds".into()]
}
fn default_target_path() -> String {
    "forge_target".into()
}

#[derive(Debug, Clone, Default, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ModelDefaults {
    pub materialized: Option<Materialized>,
    #[serde(default)]
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SeedConfig {
    /// seed を置くスキーマ(ターゲットのスキーマとは連結しない)
    #[serde(default = "default_seed_schema")]
    pub schema: String,
}

impl Default for SeedConfig {
    fn default() -> Self {
        Self {
            schema: default_seed_schema(),
        }
    }
}

fn default_seed_schema() -> String {
    "raw".into()
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Materialized {
    #[default]
    View,
    Table,
    Incremental,
    Seed,
}

impl std::fmt::Display for Materialized {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Materialized::View => "view",
            Materialized::Table => "table",
            Materialized::Incremental => "incremental",
            Materialized::Seed => "seed",
        })
    }
}

impl ProjectConfig {
    pub fn load(root: &Path) -> Result<Self> {
        let path = root.join(PROJECT_FILE);
        let text = std::fs::read_to_string(&path)
            .with_context(|| format!("{} が読めません", path.display()))?;
        toml::from_str(&text).with_context(|| format!("{} の形式が不正です", path.display()))
    }
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct OutputRaw {
    path: String,
    schema: String,
    #[serde(default)]
    attach: Vec<AttachRaw>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct AttachRaw {
    path: String,
    alias: String,
    #[serde(default)]
    read_only: bool,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct ProfileRaw {
    target: String,
    outputs: BTreeMap<String, OutputRaw>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Attach {
    pub path: PathBuf,
    pub alias: String,
    pub read_only: bool,
}

/// 解決済みの接続先(DuckDB ファイル)。
#[derive(Debug, Clone, PartialEq)]
pub struct Target {
    pub name: String,
    pub path: PathBuf,
    pub schema: String,
    pub attach: Vec<Attach>,
}

impl Target {
    /// DuckDB のカタログ名(ファイル名の stem。`prod.duckdb` → `prod`)。
    pub fn catalog(&self) -> String {
        catalog_of(&self.path)
    }

    /// 選んだ出力だけを環境変数展開する。相対パスは profiles.toml のあるディレクトリ基準。
    pub fn load(
        profiles_dir: &Path,
        profile: &str,
        target: Option<&str>,
        lookup: impl Fn(&str) -> Option<String>,
    ) -> Result<Self> {
        let path = profiles_dir.join(PROFILES_FILE);
        let text = std::fs::read_to_string(&path)
            .with_context(|| format!("{} が読めません", path.display()))?;
        let mut all: BTreeMap<String, ProfileRaw> = toml::from_str(&text)
            .with_context(|| format!("{} の形式が不正です", path.display()))?;
        let p = all
            .remove(profile)
            .ok_or_else(|| anyhow!("profiles.toml にプロファイル {profile} がありません"))?;
        let name = target.map(str::to_string).unwrap_or(p.target);
        let Some(o) = p.outputs.get(&name) else {
            bail!(
                "ターゲット {name} がありません(候補: {})",
                p.outputs.keys().cloned().collect::<Vec<_>>().join(", ")
            );
        };
        let ex = |s: &str| crate::env::expand_with(s, &lookup);
        let abs = |s: &str| -> Result<PathBuf> {
            let p = PathBuf::from(ex(s)?);
            Ok(if p.is_absolute() {
                p
            } else {
                profiles_dir.join(p)
            })
        };
        let attach = o
            .attach
            .iter()
            .map(|a| {
                Ok(Attach {
                    path: abs(&a.path)?,
                    alias: a.alias.clone(),
                    read_only: a.read_only,
                })
            })
            .collect::<Result<Vec<_>>>()?;
        Ok(Target {
            path: abs(&o.path)?,
            schema: sanitize_identifier(&ex(&o.schema)?),
            attach,
            name,
        })
    }
}

pub fn catalog_of(path: &Path) -> String {
    path.file_stem()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| "memory".into())
}

pub fn sanitize_identifier(s: &str) -> String {
    s.chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '_' {
                c
            } else {
                '_'
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    const PROFILES: &str = r#"
[p]
target = "dev"

[p.outputs.dev]
path = "warehouse/dev.duckdb"
schema = "analytics"

[p.outputs.ci]
path = "warehouse/ci.duckdb"
schema = "analytics_ci_pr${PR_NUMBER:-local}"
attach = [{ path = "warehouse/prod.duckdb", alias = "prod", read_only = true }]
"#;

    #[test]
    fn loads_targets() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join(PROFILES_FILE), PROFILES).unwrap();
        let none = |_: &str| None;
        let dev = Target::load(dir.path(), "p", None, none).unwrap();
        assert_eq!(dev.name, "dev");
        assert_eq!(dev.catalog(), "dev");
        assert!(dev.path.is_absolute());
        let ci = Target::load(dir.path(), "p", Some("ci"), |k| {
            (k == "PR_NUMBER").then(|| "12".into())
        })
        .unwrap();
        assert_eq!(ci.schema, "analytics_ci_pr12");
        assert_eq!(ci.attach[0].alias, "prod");
        assert!(ci.attach[0].read_only);
        assert!(Target::load(dir.path(), "p", Some("nope"), none).is_err());
    }
}

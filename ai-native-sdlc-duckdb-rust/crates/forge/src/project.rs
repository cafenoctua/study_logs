//! プロジェクトの読み込み: SQL モデル・seed(CSV)・YAML・設定を集めてグラフにする。

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use walkdir::WalkDir;

use crate::config::{Materialized, ProjectConfig, Target};
use crate::graph::Graph;
use crate::schema::{DataTest, Freshness, ModelDoc, SchemaFile};
use crate::template::{self, Resolver};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum OneOrMany {
    One(String),
    Many(Vec<String>),
}

/// モデルごとの設定(ディレクトリ既定値 + SQL 内の config())。
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ModelConfig {
    #[serde(default)]
    pub materialized: Materialized,
    /// incremental の更新キー(delete+insert)
    pub unique_key: Option<OneOrMany>,
    #[serde(default)]
    pub tags: Vec<String>,
}

impl ModelConfig {
    pub fn unique_keys(&self) -> Vec<String> {
        match &self.unique_key {
            None => vec![],
            Some(OneOrMany::One(k)) => vec![k.clone()],
            Some(OneOrMany::Many(ks)) => ks.clone(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct TestNode {
    /// 例: `unique_fct_orders_order_id`
    pub name: String,
    pub model: String,
    pub column: String,
    pub test: DataTest,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum NodeKind {
    Model,
    Seed,
}

#[derive(Debug, Clone)]
pub struct Node {
    pub name: String,
    pub kind: NodeKind,
    /// プロジェクトルートからの相対パス
    pub path: PathBuf,
    /// models/ 直下のフォルダ名(staging / marts など)
    pub group: String,
    /// モデルの SQL(seed は空)
    pub raw_sql: String,
    pub config: ModelConfig,
    pub refs: BTreeSet<String>,
    pub sources: BTreeSet<(String, String)>,
    pub doc: Option<ModelDoc>,
    pub tests: Vec<TestNode>,
    /// state:modified の判定に使う(SQL / CSV・設定・YAML のどれかが変わると変わる)
    pub checksum: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SourceRel {
    pub database: Option<String>,
    pub schema: String,
    pub table: String,
    pub loaded_at_field: Option<String>,
    pub freshness: Option<Freshness>,
}

/// DuckDB の `カタログ.スキーマ.テーブル`。
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Relation {
    pub database: String,
    pub schema: String,
    pub name: String,
}

impl std::fmt::Display for Relation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}.{}.{}", self.database, self.schema, self.name)
    }
}

pub struct Project {
    pub root: PathBuf,
    pub config: ProjectConfig,
    pub nodes: BTreeMap<String, Node>,
    pub sources: BTreeMap<(String, String), SourceRel>,
    pub graph: Graph,
}

fn sorted_files(base: &Path) -> Result<Vec<PathBuf>> {
    if !base.exists() {
        return Ok(vec![]);
    }
    let mut v: Vec<PathBuf> = WalkDir::new(base)
        .into_iter()
        .collect::<std::result::Result<Vec<_>, _>>()?
        .into_iter()
        .filter(|e| e.file_type().is_file())
        .map(|e| e.into_path())
        .collect();
    v.sort();
    Ok(v)
}

fn sha(parts: &[&[u8]]) -> String {
    let mut h = Sha256::new();
    for p in parts {
        h.update(p);
        h.update([0u8]);
    }
    hex::encode(h.finalize())
}

impl Project {
    pub fn load(root: &Path) -> Result<Self> {
        let config = ProjectConfig::load(root)?;
        let mut sql_files = Vec::new();
        let mut docs: BTreeMap<String, ModelDoc> = BTreeMap::new();
        let mut sources = BTreeMap::new();

        for mp in &config.model_paths {
            let base = root.join(mp);
            for p in sorted_files(&base)? {
                match p.extension().and_then(|x| x.to_str()) {
                    Some("sql") => sql_files.push((base.clone(), p)),
                    Some("yml" | "yaml") => {
                        let text = std::fs::read_to_string(&p)?;
                        let f: SchemaFile = serde_yaml::from_str(&text)
                            .with_context(|| format!("{} の形式が不正です", p.display()))?;
                        for s in f.sources {
                            for t in &s.tables {
                                let key = (s.name.clone(), t.name.clone());
                                let rel = SourceRel {
                                    database: s.database.clone(),
                                    schema: s.schema.clone().unwrap_or_else(|| s.name.clone()),
                                    table: t.identifier.clone().unwrap_or_else(|| t.name.clone()),
                                    loaded_at_field: t
                                        .loaded_at_field
                                        .clone()
                                        .or_else(|| s.loaded_at_field.clone()),
                                    freshness: t.freshness.clone().or_else(|| s.freshness.clone()),
                                };
                                if sources.insert(key.clone(), rel).is_some() {
                                    bail!("ソース {}.{} が重複しています", key.0, key.1);
                                }
                            }
                        }
                        for m in f.models {
                            let name = m.name.clone();
                            if docs.insert(name.clone(), m).is_some() {
                                bail!("モデル {name} の YAML 定義が重複しています");
                            }
                        }
                    }
                    _ => {}
                }
            }
        }

        let mut nodes = BTreeMap::new();
        let mut add = |node: Node| -> Result<()> {
            if let Some(prev) = nodes.insert(node.name.clone(), node) {
                bail!(
                    "名前 {} が重複しています({})",
                    prev.name,
                    prev.path.display()
                );
            }
            Ok(())
        };
        for sp in &config.seed_paths {
            for p in sorted_files(&root.join(sp))? {
                if p.extension().and_then(|x| x.to_str()) == Some("csv") {
                    add(load_seed(root, &p, &mut docs)?)?;
                }
            }
        }
        for (base, path) in sql_files {
            add(load_model(root, &base, &path, &config, &mut docs)?)?;
        }
        if let Some(orphan) = docs.keys().next() {
            bail!("YAML にあるモデル {orphan} に対応する SQL / CSV がありません");
        }

        for n in nodes.values() {
            for s in &n.sources {
                if !sources.contains_key(s) {
                    bail!(
                        "{} が未定義のソース source('{}', '{}') を参照しています",
                        n.name,
                        s.0,
                        s.1
                    );
                }
            }
            for t in &n.tests {
                if let DataTest::Relationships { to, .. } = &t.test {
                    if !nodes.contains_key(to) {
                        bail!(
                            "{} のテストが存在しないモデル {to} を参照しています",
                            t.name
                        );
                    }
                }
            }
        }

        let deps = nodes
            .iter()
            .map(|(k, n)| (k.clone(), n.refs.clone()))
            .collect();
        let graph = Graph::new(&deps)?;
        Ok(Project {
            root: root.to_path_buf(),
            config,
            nodes,
            sources,
            graph,
        })
    }

    pub fn node(&self, name: &str) -> Result<&Node> {
        self.nodes
            .get(name)
            .with_context(|| format!("モデル {name} がありません"))
    }

    pub fn target_dir(&self) -> PathBuf {
        self.root.join(&self.config.target_path)
    }

    /// このターゲットでのテーブル位置(seed は seeds.schema、モデルはターゲットのスキーマ)。
    pub fn relation(&self, target: &Target, name: &str) -> Relation {
        let schema = match self.nodes.get(name).map(|n| n.kind) {
            Some(NodeKind::Seed) => self.config.seeds.schema.clone(),
            _ => target.schema.clone(),
        };
        Relation {
            database: target.catalog(),
            schema,
            name: name.into(),
        }
    }

    pub fn source_relation(&self, s: &SourceRel, target: &Target) -> String {
        format!(
            "{}.{}.{}",
            s.database.clone().unwrap_or_else(|| target.catalog()),
            s.schema,
            s.table
        )
    }

    /// モデル SQL を描画する。`relations` は ref() の解決先(defer 済みのもの)。
    pub fn compile(
        &self,
        name: &str,
        target: &Target,
        relations: &HashMap<String, Relation>,
        is_incremental: bool,
    ) -> Result<String> {
        let node = self.node(name)?;
        if node.kind == NodeKind::Seed {
            bail!("{name} は seed なので描画する SQL はありません");
        }
        let mut r = Resolver {
            is_incremental,
            this: relations[name].to_string(),
            ..Default::default()
        };
        for dep in &node.refs {
            r.refs.insert(dep.clone(), relations[dep].to_string());
        }
        for key in &node.sources {
            r.sources.insert(
                key.clone(),
                self.source_relation(&self.sources[key], target),
            );
        }
        template::render(&node.name, &node.raw_sql, r)
    }
}

fn tests_from_doc(name: &str, doc: Option<&ModelDoc>) -> Result<Vec<TestNode>> {
    let mut tests = Vec::new();
    for col in doc.iter().flat_map(|d| &d.columns) {
        for spec in &col.tests {
            let test = spec
                .to_test()
                .with_context(|| format!("{name}.{} のテスト定義", col.name))?;
            tests.push(TestNode {
                name: format!("{}_{name}_{}", test.kind_name(), col.name),
                model: name.into(),
                column: col.name.clone(),
                test,
            });
        }
    }
    Ok(tests)
}

fn load_seed(root: &Path, path: &Path, docs: &mut BTreeMap<String, ModelDoc>) -> Result<Node> {
    let name = path
        .file_stem()
        .and_then(|s| s.to_str())
        .context("ファイル名が不正です")?
        .to_string();
    let bytes = std::fs::read(path)?;
    let doc = docs.remove(&name);
    let config = ModelConfig {
        materialized: Materialized::Seed,
        ..Default::default()
    };
    Ok(Node {
        tests: tests_from_doc(&name, doc.as_ref())?,
        checksum: sha(&[&bytes, &serde_json::to_vec(&doc)?]),
        name,
        kind: NodeKind::Seed,
        path: path.strip_prefix(root).unwrap_or(path).to_path_buf(),
        group: "seeds".into(),
        raw_sql: String::new(),
        config,
        refs: BTreeSet::new(),
        sources: BTreeSet::new(),
        doc,
    })
}

fn load_model(
    root: &Path,
    base: &Path,
    path: &Path,
    config: &ProjectConfig,
    docs: &mut BTreeMap<String, ModelDoc>,
) -> Result<Node> {
    let name = path
        .file_stem()
        .and_then(|s| s.to_str())
        .context("ファイル名が不正です")?
        .to_string();
    let raw_sql = std::fs::read_to_string(path)?;
    let rel_to_models = path.strip_prefix(base).unwrap_or(path);
    let group = if rel_to_models.components().count() > 1 {
        rel_to_models
            .components()
            .next()
            .map(|c| c.as_os_str().to_string_lossy().to_string())
            .unwrap_or_default()
    } else {
        String::new()
    };

    let captured = template::parse(&name, &raw_sql)?;

    // 既定値 → SQL 内 config() の順に上書き
    let defaults = config.models.get(&group).cloned().unwrap_or_default();
    let mut merged = serde_json::Map::new();
    if let Some(m) = defaults.materialized {
        merged.insert("materialized".into(), serde_json::to_value(m)?);
    }
    if !defaults.tags.is_empty() {
        merged.insert("tags".into(), serde_json::to_value(&defaults.tags)?);
    }
    merged.extend(captured.config.clone());
    let cfg: ModelConfig = serde_json::from_value(serde_json::Value::Object(merged))
        .with_context(|| format!("{name} の config() が不正です"))?;
    if cfg.materialized == Materialized::Seed {
        bail!("{name}: materialized='seed' はモデルには使えません");
    }
    if cfg.materialized == Materialized::Incremental && cfg.unique_key.is_none() {
        eprintln!("注意: {name} は unique_key のない incremental なので追記(append)になります");
    }

    let doc = docs.remove(&name);
    Ok(Node {
        tests: tests_from_doc(&name, doc.as_ref())?,
        checksum: sha(&[
            raw_sql.as_bytes(),
            &serde_json::to_vec(&cfg)?,
            &serde_json::to_vec(&doc)?,
        ]),
        name,
        kind: NodeKind::Model,
        path: path.strip_prefix(root).unwrap_or(path).to_path_buf(),
        group,
        raw_sql,
        config: cfg,
        refs: captured.refs,
        sources: captured.sources,
        doc,
    })
}

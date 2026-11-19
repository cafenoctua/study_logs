//! manifest.json(ビルド結果の記録)と、それを使った state:modified / defer。

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::path::Path;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

use crate::config::{Materialized, Target};
use crate::project::{Project, Relation};

pub const MANIFEST_FILE: &str = "manifest.json";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Manifest {
    pub forge_version: String,
    pub generated_at: String,
    pub target: String,
    pub nodes: BTreeMap<String, ManifestNode>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ManifestNode {
    pub checksum: String,
    pub relation: Relation,
    pub materialized: Materialized,
    pub depends_on: Vec<String>,
    pub path: String,
}

impl Manifest {
    pub fn build(project: &Project, target: &Target) -> Self {
        let nodes = project
            .nodes
            .values()
            .map(|n| {
                (
                    n.name.clone(),
                    ManifestNode {
                        checksum: n.checksum.clone(),
                        relation: project.relation(target, &n.name),
                        materialized: n.config.materialized,
                        depends_on: n.refs.iter().cloned().collect(),
                        path: n.path.to_string_lossy().replace('\\', "/"),
                    },
                )
            })
            .collect();
        Manifest {
            forge_version: env!("CARGO_PKG_VERSION").into(),
            generated_at: chrono::Utc::now().to_rfc3339(),
            target: target.name.clone(),
            nodes,
        }
    }

    /// ファイルかディレクトリ(中の manifest.json)を読む。無ければ `None`。
    pub fn load_opt(path: &Path) -> Result<Option<Self>> {
        let file = if path.is_dir() {
            path.join(MANIFEST_FILE)
        } else {
            path.to_path_buf()
        };
        if !file.exists() {
            return Ok(None);
        }
        let text = std::fs::read_to_string(&file)?;
        let m = serde_json::from_str(&text)
            .with_context(|| format!("{} の形式が不正です", file.display()))?;
        Ok(Some(m))
    }

    pub fn write(&self, dir: &Path) -> Result<()> {
        std::fs::create_dir_all(dir)?;
        std::fs::write(dir.join(MANIFEST_FILE), serde_json::to_string_pretty(self)?)?;
        Ok(())
    }

    /// 比較元(本番)から見て、新規または中身が変わったモデル。
    pub fn modified(&self, project: &Project) -> BTreeSet<String> {
        project
            .nodes
            .values()
            .filter(|n| {
                self.nodes
                    .get(&n.name)
                    .map_or(true, |m| m.checksum != n.checksum)
            })
            .map(|n| n.name.clone())
            .collect()
    }
}

/// ref() の解決先を決める。
/// defer 有効時は「今回ビルドしないモデル」を比較元(本番)のテーブルに向ける。
/// これで CI は変更したモデルとその下流だけを作れば済む
/// (CI ターゲットは本番の DuckDB ファイルを read_only で attach しておく)。
pub fn resolve_relations(
    project: &Project,
    target: &Target,
    selected: &BTreeSet<String>,
    defer_to: Option<&Manifest>,
) -> HashMap<String, Relation> {
    project
        .nodes
        .keys()
        .map(|name| {
            let deferred = defer_to
                .filter(|_| !selected.contains(name))
                .and_then(|m| m.nodes.get(name))
                .map(|m| m.relation.clone());
            (
                name.clone(),
                deferred.unwrap_or_else(|| project.relation(target, name)),
            )
        })
        .collect()
}

//! forge: DuckDB 向けの SQL 変換ツール。
//!
//! dbt の考え方(ref/source/seed、マテリアライズ、データテスト、state:modified による
//! Slim CI、defer)のうち、このサンプルで使う部分だけを Rust で実装したもの。

pub mod bqcheck;
pub mod config;
pub mod env;
pub mod graph;
pub mod lint;
pub mod materialize;
pub mod ops;
pub mod project;
pub mod runner;
pub mod schema;
pub mod select;
pub mod state;
pub mod template;
pub mod warehouse;

use std::collections::{BTreeSet, HashMap};
use std::path::PathBuf;

use anyhow::Result;

use config::Target;
use project::{NodeKind, Project, Relation};

/// 選んだモデルを描画して `<target-path>/compiled/<元のパス>` に書き出す。
pub fn write_compiled(
    project: &Project,
    target: &Target,
    selected: &BTreeSet<String>,
    relations: &HashMap<String, Relation>,
) -> Result<Vec<PathBuf>> {
    let base = project.target_dir().join("compiled");
    let mut written = Vec::new();
    for name in selected {
        let node = project.node(name)?;
        if node.kind == NodeKind::Seed {
            continue;
        }
        let sql = project.compile(name, target, relations, false)?;
        let out = base.join(&node.path);
        if let Some(parent) = out.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(&out, sql)?;
        written.push(out);
    }
    Ok(written)
}

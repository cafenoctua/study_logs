//! SQL lint: モデルを描画してから sqruff(Rust 製の SQL リンター)にかける。
//! テンプレートの誤り(存在しない ref など)も描画の段階で分かる。

use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{bail, Context, Result};

use crate::config::Target;
use crate::project::{NodeKind, Project};
use crate::state;

pub struct LintOutcome {
    pub ok: bool,
    pub output: String,
    pub files: Vec<PathBuf>,
}

/// 接続せずに描画するためのターゲット。
fn offline_target() -> Target {
    Target {
        name: "lint".into(),
        path: "lint".into(),
        schema: "analytics".into(),
        attach: vec![],
    }
}

/// 指定モデル(空なら全モデル)を `forge_target/lint/` に描画する。
pub fn render_for_lint(project: &Project, models: &[String]) -> Result<Vec<PathBuf>> {
    let target = offline_target();
    let all = project.nodes.keys().cloned().collect();
    let rels = state::resolve_relations(project, &target, &all, None);
    let names: Vec<&String> = if models.is_empty() {
        project
            .nodes
            .values()
            .filter(|n| n.kind == NodeKind::Model)
            .map(|n| &n.name)
            .collect()
    } else {
        models.iter().collect()
    };
    let mut files = Vec::new();
    for name in names {
        let node = project.node(name)?;
        let sql = project.compile(name, &target, &rels, false)?;
        let out = project.target_dir().join("lint").join(&node.path);
        std::fs::create_dir_all(out.parent().context("出力先が不正")?)?;
        std::fs::write(&out, sql)?;
        files.push(out);
    }
    Ok(files)
}

pub fn sqruff_available() -> bool {
    Command::new("sqruff")
        .arg("--version")
        .output()
        .is_ok_and(|o| o.status.success())
}

/// ファイルパス(models/ 配下の .sql)をモデル名に直す。
pub fn models_from_paths(project: &Project, paths: &[String]) -> Result<Vec<String>> {
    paths
        .iter()
        .map(|p| {
            let stem = Path::new(p)
                .file_stem()
                .and_then(|s| s.to_str())
                .unwrap_or(p);
            match project.nodes.get(stem) {
                Some(n) if n.kind == NodeKind::Model => Ok(stem.to_string()),
                _ => bail!("{p} はモデルではありません"),
            }
        })
        .collect()
}

pub fn lint(project: &Project, models: &[String]) -> Result<LintOutcome> {
    let files = render_for_lint(project, models)?;
    if !sqruff_available() {
        bail!("sqruff が見つかりません(cargo install sqruff --locked)");
    }
    let out = Command::new("sqruff")
        .arg("lint")
        .args(&files)
        .current_dir(&project.root)
        .output()?;
    let output =
        String::from_utf8_lossy(&out.stdout).to_string() + &String::from_utf8_lossy(&out.stderr);
    Ok(LintOutcome {
        ok: out.status.success(),
        output,
        files,
    })
}

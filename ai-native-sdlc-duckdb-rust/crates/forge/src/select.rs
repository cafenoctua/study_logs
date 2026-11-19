//! `--select` の解釈。
//!
//! - `fct_orders`         : そのモデル
//! - `fct_orders+`        : と、その下流すべて
//! - `+fct_orders`        : と、その上流すべて
//! - `state:modified`     : 比較元 manifest から変わったモデル(`--state` が必要)
//! - `tag:daily` / `path:models/marts`
//!
//! 空白またはカンマ区切りは和集合。何も指定しなければ全モデル。

use std::collections::BTreeSet;

use anyhow::{bail, Result};

use crate::project::Project;
use crate::state::Manifest;

pub fn select(
    project: &Project,
    exprs: &[String],
    state: Option<&Manifest>,
) -> Result<BTreeSet<String>> {
    let tokens: Vec<&str> = exprs
        .iter()
        .flat_map(|e| e.split(|c: char| c == ',' || c.is_whitespace()))
        .filter(|t| !t.is_empty())
        .collect();
    if tokens.is_empty() {
        return Ok(project.nodes.keys().cloned().collect());
    }
    let mut out = BTreeSet::new();
    for tok in tokens {
        let (up, rest) = match tok.strip_prefix('+') {
            Some(r) => (true, r),
            None => (false, tok),
        };
        let (down, core) = match rest.strip_suffix('+') {
            Some(r) => (true, r),
            None => (false, rest),
        };
        let base = base_set(project, core, state)?;
        for n in &base {
            if up {
                out.extend(project.graph.ancestors(n));
            }
            if down {
                out.extend(project.graph.descendants(n));
            }
        }
        out.extend(base);
    }
    Ok(out)
}

fn base_set(project: &Project, core: &str, state: Option<&Manifest>) -> Result<BTreeSet<String>> {
    if let Some(m) = core.strip_prefix("state:") {
        if m != "modified" {
            bail!("state: は modified のみ対応しています");
        }
        let Some(manifest) = state else {
            bail!("state:modified には --state(比較元の manifest)が必要です");
        };
        return Ok(manifest.modified(project));
    }
    if let Some(tag) = core.strip_prefix("tag:") {
        return Ok(project
            .nodes
            .values()
            .filter(|n| n.config.tags.iter().any(|t| t == tag))
            .map(|n| n.name.clone())
            .collect());
    }
    if let Some(p) = core.strip_prefix("path:") {
        let p = p.trim_end_matches('/');
        return Ok(project
            .nodes
            .values()
            .filter(|n| {
                let np = n.path.to_string_lossy().replace('\\', "/");
                np == p || np.starts_with(&format!("{p}/"))
            })
            .map(|n| n.name.clone())
            .collect());
    }
    if project.nodes.contains_key(core) {
        return Ok([core.to_string()].into());
    }
    bail!("--select の {core} に一致するモデルがありません")
}

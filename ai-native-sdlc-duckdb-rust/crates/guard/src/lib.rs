//! Claude Code フックの判定ロジック。
//!
//! Claude Code はツール呼び出しの情報を JSON で標準入力に渡す。終了コード 2 で終わると、
//! PreToolUse ではツール実行がブロックされ、PostToolUse では stderr が Claude に返ってその場で直させる。
//! 解析できない入力は通す(fail-open)。

use std::path::{Component, Path, PathBuf};

use anyhow::Result;
use globset::{Glob, GlobSet, GlobSetBuilder};
use serde_json::Value;

/// 常に保護するパス(人間だけが変更する)。
pub const ALWAYS: &[&str] = &[
    "profiles.toml",
    "scripts/deploy.sh",
    "workflows/deploy.yml",
    ".github/workflows/deploy.yml",
    ".claude/settings.json",
    // フック自身のコード。ここを書き換えられると保護が外れる
    "crates/guard/*",
];

/// LOCK_TESTS=1 のときに追加で保護する(バグ修正中のテスト改変を防ぐ)。
/// Rust の単体テスト(#[cfg(test)])はソースと同じファイルにあるので守れない。
/// 守りたいテストは `crates/*/tests/` に置く。
pub const TESTS: &[&str] = &[
    "crates/*/tests/*",
    "models/*schema.yml",
    "models/**/schema.yml",
];

pub fn protected_set(lock_tests: bool) -> GlobSet {
    let mut b = GlobSetBuilder::new();
    let extra: &[&str] = if lock_tests { TESTS } else { &[] };
    for p in ALWAYS.iter().chain(extra) {
        // `*` は `/` もまたぐ(Python の fnmatch と同じ)
        b.add(Glob::new(p).expect("固定パターン"));
    }
    b.build().expect("固定パターン")
}

/// `..` や `.` を字句的に畳む(`models/../profiles.toml` を見逃さないため)。
pub fn normalize(p: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for c in p.components() {
        match c {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            other => out.push(other),
        }
    }
    out
}

pub fn relative_path(file_path: &str, root: &str) -> String {
    let p = normalize(Path::new(file_path));
    let rel = if !root.is_empty() && p.is_absolute() {
        p.strip_prefix(normalize(Path::new(root)))
            .map(Path::to_path_buf)
            .unwrap_or(p)
    } else {
        p
    };
    rel.to_string_lossy().replace('\\', "/")
}

pub fn file_path(payload: &Value) -> Option<&str> {
    let ti = &payload["tool_input"];
    ti["file_path"]
        .as_str()
        .or(ti["notebook_path"].as_str())
        .filter(|s| !s.is_empty())
}

/// 保護対象なら理由を返す。
pub fn check(path: &str, root: &str, lock_tests: bool) -> Option<String> {
    let rel = relative_path(path, root);
    protected_set(lock_tests)
        .is_match(&rel)
        .then(|| format!("blocked: {rel} は保護対象です。人間に変更を依頼してください。"))
}

/// lint 対象(models/ 配下の .sql)ならそのパス。
pub fn target_sql<'a>(payload: &'a Value, root: &str) -> Option<&'a str> {
    let p = file_path(payload)?;
    let rel = relative_path(p, root);
    (rel.ends_with(".sql") && format!("/{rel}").contains("/models/")).then_some(p)
}

#[derive(Debug, PartialEq)]
pub enum Decision {
    Allow,
    /// stderr に出すメッセージ
    Block(String),
}

/// PreToolUse
pub fn protect_paths(payload: &Value, root: &str, lock_tests: bool) -> Decision {
    match file_path(payload).and_then(|p| check(p, root, lock_tests)) {
        Some(msg) => Decision::Block(msg),
        None => Decision::Allow,
    }
}

/// PostToolUse: 編集したモデルだけを描画して sqruff で lint する。
pub fn lint_sql(payload: &Value, root: &str) -> Result<Decision> {
    let Some(path) = target_sql(payload, root) else {
        return Ok(Decision::Allow);
    };
    // 編集でプロジェクトが読めなくなった(存在しない ref、YAML の誤りなど)ときも Claude に返す
    let project = match forge::project::Project::load(Path::new(root)) {
        Ok(p) => p,
        Err(e) => {
            return Ok(Decision::Block(format!(
                "{path} の編集後、プロジェクトを読み込めません:\n{e:#}"
            )))
        }
    };
    let models = match forge::lint::models_from_paths(&project, &[path.to_string()]) {
        Ok(m) => m,
        Err(_) => return Ok(Decision::Allow),
    };
    if !forge::lint::sqruff_available() {
        // 描画だけは確認する(存在しない ref などはここで分かる)
        return Ok(match forge::lint::render_for_lint(&project, &models) {
            Ok(_) => Decision::Allow,
            Err(e) => Decision::Block(format!("{path} を描画できません:\n{e:#}")),
        });
    }
    match forge::lint::lint(&project, &models) {
        Ok(o) if o.ok => Ok(Decision::Allow),
        Ok(o) => {
            let tail: String = o
                .output
                .chars()
                .rev()
                .take(4000)
                .collect::<Vec<_>>()
                .into_iter()
                .rev()
                .collect();
            Ok(Decision::Block(format!(
                "lint violations in {path}(描画後の SQL を検査。行番号は元ファイルと少しずれます):\n{tail}"
            )))
        }
        Err(e) => Ok(Decision::Block(format!("{path} を描画できません:\n{e:#}"))),
    }
}

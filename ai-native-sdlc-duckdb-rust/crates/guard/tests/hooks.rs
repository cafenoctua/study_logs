//! PR #38 の tests/test_hooks.py を移したもの(+ Rust 版で増えた保護対象)。

use std::io::Write;
use std::process::{Command, Stdio};

use guard::{check, target_sql};
use serde_json::json;

const ROOT: &str = "/repo";

#[test]
fn blocks_profiles_and_deploy() {
    assert!(check("/repo/profiles.toml", ROOT, false).is_some());
    assert!(check("/repo/scripts/deploy.sh", ROOT, false).is_some());
    assert!(check("/repo/.claude/settings.json", ROOT, false).is_some());
    assert!(check("/repo/crates/guard/src/lib.rs", ROOT, false).is_some());
    assert!(check("/repo/models/../profiles.toml", ROOT, false).is_some());
}

#[test]
fn allows_models() {
    assert!(check("/repo/models/marts/fct_orders.sql", ROOT, false).is_none());
    assert!(check("/repo/crates/forge/src/lib.rs", ROOT, false).is_none());
}

#[test]
fn lock_tests_protects_tests_and_schema() {
    assert!(check("/repo/crates/monitor/tests/severity.rs", ROOT, false).is_none());
    assert!(check("/repo/crates/monitor/tests/severity.rs", ROOT, true).is_some());
    assert!(check("/repo/models/marts/schema.yml", ROOT, true).is_some());
}

fn run(payload: &str) -> i32 {
    let mut child = Command::new(env!("CARGO_BIN_EXE_guard"))
        .arg("protect-paths")
        .env("CLAUDE_PROJECT_DIR", ROOT)
        .env_remove("LOCK_TESTS")
        .stdin(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(payload.as_bytes())
        .unwrap();
    child.wait().unwrap().code().unwrap()
}

#[test]
fn hook_exit_codes() {
    assert_eq!(
        run(&json!({"tool_input": {"file_path": "/repo/profiles.toml"}}).to_string()),
        2
    );
    assert_eq!(
        run(&json!({"tool_input": {"file_path": "/repo/models/x.sql"}}).to_string()),
        0
    );
    assert_eq!(
        run(&json!({"tool_input": {"notebook_path": "/repo/.claude/settings.json"}}).to_string()),
        2
    );
    assert_eq!(run("not json"), 0); // fail-open
}

#[test]
fn lint_targets_only_model_sql() {
    assert!(target_sql(
        &json!({"tool_input": {"file_path": "/repo/models/a.sql"}}),
        ROOT
    )
    .is_some());
    assert!(target_sql(
        &json!({"tool_input": {"file_path": "/repo/README.md"}}),
        ROOT
    )
    .is_none());
    assert!(target_sql(
        &json!({"tool_input": {"file_path": "/repo/monitoring/sql/kpi.sql"}}),
        ROOT
    )
    .is_none());
}

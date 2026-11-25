//! `.claude/settings.json` から呼ぶ:
//!   guard protect-paths   # PreToolUse
//!   guard lint-sql        # PostToolUse

use std::io::Read;
use std::process::ExitCode;

use guard::Decision;

fn main() -> ExitCode {
    let mode = std::env::args().nth(1).unwrap_or_default();
    let mut input = String::new();
    if std::io::stdin().read_to_string(&mut input).is_err() {
        return ExitCode::SUCCESS;
    }
    let Ok(payload) = serde_json::from_str::<serde_json::Value>(&input) else {
        return ExitCode::SUCCESS; // fail-open
    };
    let root = std::env::var("CLAUDE_PROJECT_DIR")
        .ok()
        .or_else(|| {
            std::env::current_dir()
                .ok()
                .map(|p| p.to_string_lossy().to_string())
        })
        .unwrap_or_default();

    let decision = match mode.as_str() {
        "protect-paths" => guard::protect_paths(
            &payload,
            &root,
            std::env::var("LOCK_TESTS").as_deref() == Ok("1"),
        ),
        "lint-sql" => match guard::lint_sql(&payload, &root) {
            Ok(d) => d,
            Err(e) => {
                eprintln!("guard lint-sql の内部エラー(作業は続行): {e:#}");
                return ExitCode::SUCCESS;
            }
        },
        _ => {
            eprintln!("usage: guard <protect-paths|lint-sql>");
            return ExitCode::from(1);
        }
    };
    match decision {
        Decision::Allow => ExitCode::SUCCESS,
        Decision::Block(msg) => {
            eprintln!("{msg}");
            ExitCode::from(2)
        }
    }
}

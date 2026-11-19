//! monitor collect / detect / seed-history
//!
//! MONITOR_MODE=shadow(既定): 記録のみ
//! MONITOR_MODE=active        : 段階2以上で診断プロンプトを artifacts/diagnose/ に出力
//!                              (RUN_CLAUDE=1 かつ claude CLI があれば `claude -p` に読み取り専用で渡す)

use std::path::PathBuf;
use std::process::{Command, ExitCode};

use anyhow::Result;
use clap::{Parser, Subcommand};
use forge::warehouse::Db;
use monitor::{Config, Mode};

#[derive(Parser)]
#[command(name = "monitor", version, about = "本番指標の収集と σ 段階判定")]
struct Cli {
    #[arg(long, global = true, default_value = ".", env = "FORGE_PROJECT_DIR")]
    project_dir: PathBuf,
    /// 省略時は <project-dir>/monitoring/metrics.yml
    #[arg(long, global = true)]
    config: Option<PathBuf>,
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// 指標を取得して ops.metric_snapshots に追記する
    Collect,
    /// 段階判定して ops.monitor_events に記録する
    Detect {
        #[arg(long, env = "MONITOR_MODE", default_value = "shadow", value_parser = ["shadow", "active"])]
        mode: String,
    },
    /// 監視デモ用に過去28日分の擬似スナップショットを投入する
    SeedHistory {
        /// 最新値に異常(行数3倍)を入れる
        #[arg(long)]
        anomaly: bool,
    },
}

/// 診断用 Claude に渡すツール。編集系は渡さない(DB は read_only で開く)。
const ALLOWED_TOOLS: &str =
    "Read,Grep,Bash(git log:*),Bash(git diff:*),Bash(git show:*),Bash(forge query --read-only:*)";

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("エラー: {e:#}");
            ExitCode::from(2)
        }
    }
}

fn run() -> Result<()> {
    let cli = Cli::parse();
    let root = std::fs::canonicalize(&cli.project_dir).unwrap_or(cli.project_dir.clone());
    let cfg_path = cli
        .config
        .clone()
        .unwrap_or_else(|| root.join("monitoring/metrics.yml"));
    let db = Db::open_path(&forge::ops::prod_db_path(&root), false)?;

    match cli.cmd {
        Cmd::Collect => {
            monitor::collect(&db, &Config::load(&cfg_path)?)?;
        }
        Cmd::SeedHistory { anomaly } => {
            monitor::seed_history(&db, anomaly)?;
            println!("history seeded");
        }
        Cmd::Detect { mode } => {
            let mode = if mode == "active" {
                Mode::Active
            } else {
                Mode::Shadow
            };
            let findings = monitor::detect(&db, &Config::load(&cfg_path)?, mode)?;
            drop(db); // 診断側が read_only で開けるように閉じる
            if findings.is_empty() {
                return Ok(());
            }
            if mode == Mode::Shadow {
                println!(
                    "shadow mode: {} finding(s) recorded, no diagnosis",
                    findings.len()
                );
                return Ok(());
            }
            let path = monitor::write_diagnosis(&root, &findings)?;
            println!("diagnosis prompt -> {}", path.display());
            let has_claude = Command::new("claude")
                .arg("--version")
                .output()
                .is_ok_and(|o| o.status.success());
            if has_claude && std::env::var("RUN_CLAUDE").as_deref() == Ok("1") {
                let prompt = std::fs::read_to_string(&path)?;
                let out = Command::new("claude")
                    .args([
                        "-p",
                        &prompt,
                        "--allowedTools",
                        ALLOWED_TOOLS,
                        "--disallowedTools",
                        "Edit,Write,NotebookEdit",
                    ])
                    .current_dir(&root)
                    .output()?;
                let report = path.with_extension("report.md");
                std::fs::write(&report, &out.stdout)?;
                println!(
                    "diagnosis report -> {}  (Issue 化はローカル版では手動: gh issue create -F {})",
                    report.display(),
                    report.display()
                );
            }
        }
    }
    Ok(())
}

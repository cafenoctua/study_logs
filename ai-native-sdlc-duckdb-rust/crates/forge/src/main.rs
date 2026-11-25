use std::collections::BTreeSet;
use std::path::PathBuf;
use std::process::ExitCode;

use anyhow::{bail, Result};
use clap::{Args, Parser, Subcommand};
use forge::config::Target;
use forge::ops;
use forge::project::{NodeKind, Project};
use forge::runner::{Command, RunResults, Runner};
use forge::state::{self, Manifest};
use forge::warehouse::Db;

#[derive(Parser)]
#[command(name = "forge", version, about = "DuckDB 向けの SQL 変換ツール")]
struct Cli {
    /// forge_project.toml のあるディレクトリ
    #[arg(long, global = true, default_value = ".", env = "FORGE_PROJECT_DIR")]
    project_dir: PathBuf,
    /// profiles.toml のあるディレクトリ(省略時は project-dir)
    #[arg(long, global = true, env = "FORGE_PROFILES_DIR")]
    profiles_dir: Option<PathBuf>,
    /// profiles.toml のターゲット(dev / ci / prod)
    #[arg(long, short, global = true, env = "FORGE_TARGET")]
    target: Option<String>,
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Args, Clone, Default)]
struct Selection {
    /// 例: fct_orders+ / +fct_orders / state:modified+ / tag:daily / path:models/marts
    #[arg(long, short, num_args = 1..)]
    select: Vec<String>,
    /// 比較元の manifest(ファイルかディレクトリ)。state:modified と --defer で使う
    #[arg(long)]
    state: Option<PathBuf>,
    /// 選択外への ref() を --state 側(本番)のテーブルに向ける
    #[arg(long)]
    defer: bool,
}

#[derive(Args, Clone)]
struct RunArgs {
    #[command(flatten)]
    sel: Selection,
    /// incremental を作り直す
    #[arg(long)]
    full_refresh: bool,
}

#[derive(Subcommand)]
enum Cmd {
    /// SQL を描画して forge_target/compiled/ に書き出す(DB に接続しない)
    Compile(Selection),
    /// 選択されるノードを依存順に表示する
    Ls {
        #[command(flatten)]
        sel: Selection,
        #[arg(long, default_value = "name", value_parser = ["name", "path", "json"])]
        output: String,
    },
    /// seeds/ の CSV をテーブルにする
    Seed(RunArgs),
    /// モデルを作る
    Run(RunArgs),
    /// データテストだけを実行する
    Test(RunArgs),
    /// seed・モデルを作り、直後にそのテストを実行する(失敗したら下流はスキップ)
    Build(RunArgs),
    /// 描画した SQL を sqruff で lint する(引数なしで全モデル)
    Lint { files: Vec<String> },
    /// BigQuery で通らない書き方を接続なしで検出する
    BqCompat,
    /// 本番 DuckDB(warehouse/prod.duckdb)に SQL を流して結果を表示する
    Query {
        /// SQL 文、または .sql ファイル
        sql: String,
        /// 読み取り専用で開く(書き込みは DuckDB が拒否する)。診断用
        #[arg(long)]
        read_only: bool,
        #[arg(long, default_value = "table", value_parser = ["table", "json"])]
        format: String,
    },
    /// ops スキーマへの記録
    Ops {
        #[command(subcommand)]
        op: OpsCmd,
    },
}

#[derive(Subcommand)]
enum OpsCmd {
    /// ops スキーマとテーブルを作る(冪等)
    Init,
    /// forge_target/run_results.json を ops.run_results に保存
    UploadResults {
        /// ci / prod
        env: String,
        sha: Option<String>,
    },
    /// ops.deployments に1行
    RecordDeployment {
        sha: String,
        approver: String,
        status: String,
    },
    /// ops.ci_runs に1行
    RecordCiRun {
        sha: String,
        pr: String,
        attempt: i32,
        status: String,
    },
}

fn main() -> ExitCode {
    match real_main() {
        Ok(code) => code,
        Err(e) => {
            eprintln!("エラー: {e:#}");
            ExitCode::from(2)
        }
    }
}

fn load_target(cli: &Cli, project: &Project) -> Result<Target> {
    let dir = cli
        .profiles_dir
        .clone()
        .unwrap_or_else(|| cli.project_dir.clone());
    let dir = std::fs::canonicalize(&dir).unwrap_or(dir);
    Target::load(&dir, &project.config.profile, cli.target.as_deref(), |k| {
        std::env::var(k).ok()
    })
}

struct Resolved {
    selected: BTreeSet<String>,
    defer_to: Option<Manifest>,
}

fn resolve_selection(project: &Project, sel: &Selection) -> Result<Resolved> {
    if sel.defer && sel.state.is_none() {
        bail!("--defer には --state が必要です");
    }
    let state = match &sel.state {
        Some(p) => {
            let m = Manifest::load_opt(p)?;
            if m.is_none() {
                eprintln!(
                    "注意: 比較元 manifest が {} にありません。全ノードを変更ありとして扱い、defer もしません",
                    p.display()
                );
            }
            m
        }
        None => None,
    };
    let uses_state = sel.select.iter().any(|s| s.contains("state:"));
    let selected = if uses_state && state.is_none() && sel.state.is_some() {
        project.nodes.keys().cloned().collect()
    } else {
        forge::select::select(project, &sel.select, state.as_ref())?
    };
    Ok(Resolved {
        selected,
        defer_to: if sel.defer { state } else { None },
    })
}

fn real_main() -> Result<ExitCode> {
    let cli = Cli::parse();
    let root = std::fs::canonicalize(&cli.project_dir).unwrap_or_else(|_| cli.project_dir.clone());

    match &cli.cmd {
        Cmd::Compile(sel) => {
            let project = Project::load(&root)?;
            let target = load_target(&cli, &project)?;
            let r = resolve_selection(&project, sel)?;
            let rels =
                state::resolve_relations(&project, &target, &r.selected, r.defer_to.as_ref());
            for p in forge::write_compiled(&project, &target, &r.selected, &rels)? {
                println!("{}", p.display());
            }
            Manifest::build(&project, &target).write(&project.target_dir())?;
            Ok(ExitCode::SUCCESS)
        }
        Cmd::Ls { sel, output } => {
            let project = Project::load(&root)?;
            let r = resolve_selection(&project, sel)?;
            let order: Vec<String> = project
                .graph
                .topo_order()?
                .into_iter()
                .filter(|n| r.selected.contains(n))
                .collect();
            match output.as_str() {
                "path" => order
                    .iter()
                    .for_each(|n| println!("{}", project.nodes[n].path.display())),
                "json" => println!("{}", serde_json::to_string_pretty(&order)?),
                _ => order.iter().for_each(|n| println!("{n}")),
            }
            Ok(ExitCode::SUCCESS)
        }
        Cmd::Seed(a) | Cmd::Run(a) | Cmd::Test(a) | Cmd::Build(a) => {
            let command = match &cli.cmd {
                Cmd::Seed(_) => Command::Seed,
                Cmd::Run(_) => Command::Run,
                Cmd::Test(_) => Command::Test,
                _ => Command::Build,
            };
            let project = Project::load(&root)?;
            let target = load_target(&cli, &project)?;
            let r = resolve_selection(&project, &a.sel)?;
            let rels =
                state::resolve_relations(&project, &target, &r.selected, r.defer_to.as_ref());
            let seed_schema = project.config.seeds.schema.clone();
            let db = Db::open_target(&target, &[&target.schema, &seed_schema])?;
            eprintln!(
                "{} {} ノード(target={}, {} / schema {})",
                command.as_str(),
                r.selected.len(),
                target.name,
                target.path.display(),
                target.schema
            );
            let runner = Runner {
                project: &project,
                db: &db,
                target: &target,
                relations: &rels,
                full_refresh: a.full_refresh,
                verbose: true,
            };
            let results = runner.execute(command, &r.selected)?;
            results.write(&project.target_dir())?;
            Manifest::build(&project, &target).write(&project.target_dir())?;
            let bad = results.results.iter().filter(|r| r.status.is_bad()).count();
            eprintln!(
                "完了: {} 件中 失敗 {bad} 件({:.2}s)",
                results.results.len(),
                results.elapsed_s
            );
            Ok(if results.has_failures() {
                ExitCode::FAILURE
            } else {
                ExitCode::SUCCESS
            })
        }
        Cmd::Lint { files } => {
            let project = Project::load(&root)?;
            let models = forge::lint::models_from_paths(&project, files)?;
            let out = forge::lint::lint(&project, &models)?;
            print!("{}", out.output);
            Ok(if out.ok {
                ExitCode::SUCCESS
            } else {
                ExitCode::FAILURE
            })
        }
        Cmd::BqCompat => {
            let project = Project::load(&root)?;
            let findings = forge::bqcheck::check_project(&project)?;
            let n = project
                .nodes
                .values()
                .filter(|n| n.kind == NodeKind::Model)
                .count();
            for f in &findings {
                println!("{}: {}", f.model, f.message);
            }
            eprintln!(
                "BigQuery 互換チェック: {n} モデル / 指摘 {} 件(構文のみ。型は見ない)",
                findings.len()
            );
            Ok(if findings.is_empty() {
                ExitCode::SUCCESS
            } else {
                ExitCode::FAILURE
            })
        }
        Cmd::Query {
            sql,
            read_only,
            format,
        } => {
            let text = if sql.ends_with(".sql") {
                std::fs::read_to_string(sql)?
            } else {
                sql.clone()
            };
            let db = Db::open_path(&ops::prod_db_path(&root), *read_only)?;
            // 複数文のファイル(DDL など)にも対応: 最後の文の結果だけ表示する
            let stmts: Vec<&str> = text.split(';').filter(|s| has_code(s)).collect();
            let Some((last, init)) = stmts.split_last() else {
                bail!("SQL が空です")
            };
            for s in init {
                db.execute(s)?;
            }
            let res = db.query(last)?;
            if format == "json" {
                println!("{}", serde_json::to_string_pretty(&res.records())?);
            } else if !res.columns.is_empty() {
                println!("{}", res.to_table());
                eprintln!("({} 行)", res.rows.len());
            }
            Ok(ExitCode::SUCCESS)
        }
        Cmd::Ops { op } => {
            let db = Db::open_path(&ops::prod_db_path(&root), false)?;
            match op {
                OpsCmd::Init => {
                    ops::init(&db)?;
                    eprintln!("ops schema ready");
                }
                OpsCmd::UploadResults { env, sha } => {
                    let project = Project::load(&root)?;
                    let rr = RunResults::load(&project.target_dir())?;
                    let n = ops::upload_results(&db, &rr, env, sha.as_deref())?;
                    eprintln!("uploaded {n} run results ({env})");
                }
                OpsCmd::RecordDeployment {
                    sha,
                    approver,
                    status,
                } => {
                    ops::record_deployment(&db, sha, approver, status)?;
                    eprintln!("recorded deployment: {sha} {approver} {status}");
                }
                OpsCmd::RecordCiRun {
                    sha,
                    pr,
                    attempt,
                    status,
                } => {
                    ops::record_ci_run(&db, sha, pr, *attempt, status)?;
                    eprintln!("recorded ci_run: {sha} pr={pr} attempt={attempt} {status}");
                }
            }
            Ok(ExitCode::SUCCESS)
        }
    }
}

/// コメントと空白だけの断片は除く。
fn has_code(s: &str) -> bool {
    s.lines().any(|l| {
        let l = l.split("--").next().unwrap_or("").trim();
        !l.is_empty()
    })
}

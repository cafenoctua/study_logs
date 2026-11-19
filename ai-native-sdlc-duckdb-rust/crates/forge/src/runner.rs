//! run / test / build / seed の実行。依存順に実行し、
//! 失敗したモデル(または build でテストが落ちたモデル)の下流はスキップする。
//! DuckDB は1ファイルに書き込めるのが1接続だけなので、直列に実行する。

use std::collections::{BTreeSet, HashMap};
use std::path::Path;
use std::time::Instant;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

use crate::config::{Materialized, Target};
use crate::materialize;
use crate::project::{NodeKind, Project, Relation, TestNode};
use crate::schema::DataTest;
use crate::warehouse::Db;

pub const RUN_RESULTS_FILE: &str = "run_results.json";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Command {
    Seed,
    Run,
    Test,
    Build,
}

impl Command {
    pub fn as_str(&self) -> &'static str {
        match self {
            Command::Seed => "seed",
            Command::Run => "run",
            Command::Test => "test",
            Command::Build => "build",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Status {
    Success,
    Error,
    Skipped,
    Pass,
    Fail,
}

impl Status {
    pub fn is_bad(&self) -> bool {
        matches!(self, Status::Error | Status::Fail)
    }
    pub fn as_str(&self) -> &'static str {
        match self {
            Status::Success => "success",
            Status::Error => "error",
            Status::Skipped => "skipped",
            Status::Pass => "pass",
            Status::Fail => "fail",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NodeResult {
    pub unique_id: String,
    pub resource_type: String,
    pub name: String,
    pub status: Status,
    pub execution_time_s: f64,
    pub message: Option<String>,
    pub failures: Option<i64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RunResults {
    pub invocation_id: String,
    /// UTC(タイムゾーンなし)
    pub generated_at: String,
    pub command: String,
    pub target: String,
    pub elapsed_s: f64,
    pub results: Vec<NodeResult>,
}

impl RunResults {
    pub fn has_failures(&self) -> bool {
        self.results.iter().any(|r| r.status.is_bad())
    }

    pub fn write(&self, dir: &Path) -> Result<()> {
        std::fs::create_dir_all(dir)?;
        std::fs::write(
            dir.join(RUN_RESULTS_FILE),
            serde_json::to_string_pretty(self)?,
        )?;
        Ok(())
    }

    pub fn load(dir: &Path) -> Result<Self> {
        let p = dir.join(RUN_RESULTS_FILE);
        let text =
            std::fs::read_to_string(&p).with_context(|| format!("{} が読めません", p.display()))?;
        Ok(serde_json::from_str(&text)?)
    }
}

pub fn utc_now() -> String {
    chrono::Utc::now()
        .naive_utc()
        .format("%Y-%m-%d %H:%M:%S%.6f")
        .to_string()
}

pub struct Runner<'a> {
    pub project: &'a Project,
    pub db: &'a Db,
    pub target: &'a Target,
    pub relations: &'a HashMap<String, Relation>,
    pub full_refresh: bool,
    /// 進捗を stderr に出す
    pub verbose: bool,
}

impl Runner<'_> {
    pub fn execute(&self, command: Command, selected: &BTreeSet<String>) -> Result<RunResults> {
        let started = Instant::now();
        let order: Vec<String> = self
            .project
            .graph
            .waves(selected)?
            .into_iter()
            .flatten()
            .filter(|n| {
                let is_seed = self.project.nodes[n].kind == NodeKind::Seed;
                match command {
                    Command::Seed => is_seed,
                    Command::Run => !is_seed,
                    Command::Test | Command::Build => true,
                }
            })
            .collect();
        let total = order.len();
        let mut blocked: BTreeSet<String> = BTreeSet::new();
        let mut results = Vec::new();

        for (i, name) in order.iter().enumerate() {
            let skip = self
                .project
                .graph
                .ancestors(name)
                .iter()
                .any(|a| blocked.contains(a));
            let rs = if skip {
                vec![self.skipped(name)]
            } else {
                self.run_node(command, name)
            };
            if self.verbose {
                for r in &rs {
                    print_result(i + 1, total, r);
                }
            }
            let blocks = |r: &NodeResult| {
                r.status.is_bad() || (r.status == Status::Skipped && r.resource_type != "test")
            };
            if command != Command::Test && rs.iter().any(blocks) {
                blocked.insert(name.clone());
            }
            results.extend(rs);
        }

        Ok(RunResults {
            invocation_id: format!(
                "{}-{}",
                chrono::Utc::now().timestamp_millis(),
                std::process::id()
            ),
            generated_at: utc_now(),
            command: command.as_str().into(),
            target: self.target.name.clone(),
            elapsed_s: started.elapsed().as_secs_f64(),
            results,
        })
    }

    fn unique_id(&self, name: &str) -> String {
        let kind = match self.project.nodes[name].kind {
            NodeKind::Seed => "seed",
            NodeKind::Model => "model",
        };
        format!("{kind}.{}.{name}", self.project.config.name)
    }

    fn run_node(&self, command: Command, name: &str) -> Vec<NodeResult> {
        let mut out = Vec::new();
        if command != Command::Test {
            let r = self.materialize(name);
            let ok = r.status == Status::Success;
            out.push(r);
            if !ok || matches!(command, Command::Run | Command::Seed) {
                return out;
            }
        }
        for t in &self.project.nodes[name].tests {
            out.push(self.run_test(t));
        }
        out
    }

    fn materialize(&self, name: &str) -> NodeResult {
        let started = Instant::now();
        let (status, message) = match self.materialize_inner(name) {
            Ok(msg) => (Status::Success, Some(msg)),
            Err(e) => (Status::Error, Some(format!("{e:#}"))),
        };
        NodeResult {
            unique_id: self.unique_id(name),
            resource_type: format!("{:?}", self.project.nodes[name].kind).to_lowercase(),
            name: name.into(),
            status,
            execution_time_s: started.elapsed().as_secs_f64(),
            message,
            failures: None,
        }
    }

    fn materialize_inner(&self, name: &str) -> Result<String> {
        let node = &self.project.nodes[name];
        let rel = &self.relations[name];
        let existing = self.db.relation_kind(rel)?;
        let drop_if = |want: &str| -> Result<()> {
            if let Some(k) = existing.as_deref().filter(|k| *k != want) {
                self.db.execute(&materialize::drop_relation(rel, k))?;
            }
            Ok(())
        };
        let compile = |inc: bool| self.project.compile(name, self.target, self.relations, inc);

        let (sql, label) = match node.config.materialized {
            Materialized::Seed => {
                drop_if("BASE TABLE")?;
                (
                    materialize::load_seed(rel, &self.project.root.join(&node.path)),
                    "seed",
                )
            }
            Materialized::View => {
                drop_if("VIEW")?;
                (materialize::create_view(rel, &compile(false)?), "view")
            }
            Materialized::Table => {
                drop_if("BASE TABLE")?;
                (materialize::create_table(rel, &compile(false)?), "table")
            }
            Materialized::Incremental => {
                let is_table = existing.as_deref() == Some("BASE TABLE");
                if is_table && !self.full_refresh {
                    let cols = self.db.columns(rel)?;
                    let label = if node.config.unique_keys().is_empty() {
                        "append"
                    } else {
                        "delete+insert"
                    };
                    (
                        materialize::incremental(rel, &node.config, &compile(true)?, &cols),
                        label,
                    )
                } else {
                    drop_if("BASE TABLE")?;
                    (
                        materialize::create_table(rel, &compile(false)?),
                        "table (full)",
                    )
                }
            }
        };
        self.db.execute(&sql)?;
        Ok(format!("{label} {rel}"))
    }

    fn run_test(&self, t: &TestNode) -> NodeResult {
        let started = Instant::now();
        let rel = &self.relations[&t.model];
        let to = match &t.test {
            DataTest::Relationships { to, .. } => self.relations.get(to),
            _ => None,
        };
        // 参照先が今回作られておらず、ターゲットにも無い(部分選択の)ときは判定できないのでスキップ
        if let Some(to_rel) = to {
            if matches!(self.db.relation_kind(to_rel), Ok(None)) {
                return NodeResult {
                    unique_id: format!("test.{}.{}", self.project.config.name, t.name),
                    resource_type: "test".into(),
                    name: t.name.clone(),
                    status: Status::Skipped,
                    execution_time_s: 0.0,
                    message: Some(format!("参照先 {to_rel} が無いのでスキップ")),
                    failures: None,
                };
            }
        }
        let sql = materialize::test_sql(&t.test, rel, &t.column, to);
        let (status, failures, message) = match self.db.query(&sql) {
            Ok(r) => match r.get_f64(0, "failures") {
                Some(0.0) => (Status::Pass, Some(0), None),
                Some(n) => (
                    Status::Fail,
                    Some(n as i64),
                    Some(format!("{n} 行が条件を満たしません")),
                ),
                None => (
                    Status::Error,
                    None,
                    Some("failures 列が返りませんでした".into()),
                ),
            },
            Err(e) => (Status::Error, None, Some(format!("{e:#}"))),
        };
        NodeResult {
            unique_id: format!("test.{}.{}", self.project.config.name, t.name),
            resource_type: "test".into(),
            name: t.name.clone(),
            status,
            execution_time_s: started.elapsed().as_secs_f64(),
            message,
            failures,
        }
    }

    fn skipped(&self, name: &str) -> NodeResult {
        NodeResult {
            unique_id: self.unique_id(name),
            resource_type: "model".into(),
            name: name.into(),
            status: Status::Skipped,
            execution_time_s: 0.0,
            message: Some("上流の失敗によりスキップ".into()),
            failures: None,
        }
    }
}

fn print_result(done: usize, total: usize, r: &NodeResult) {
    let mark = match r.status {
        Status::Success | Status::Pass => "OK  ",
        Status::Skipped => "SKIP",
        Status::Fail => "FAIL",
        Status::Error => "ERR ",
    };
    let msg = r.message.as_deref().unwrap_or("");
    eprintln!(
        "[{done}/{total}] {mark} {} {} ({:.2}s) {msg}",
        r.resource_type, r.name, r.execution_time_s
    );
}

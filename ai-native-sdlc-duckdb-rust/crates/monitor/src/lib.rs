//! 本番指標の収集(collect)・段階判定(detect)・デモ用履歴の投入(seed-history)。
//! 対象は warehouse/prod.duckdb(analytics と ops が同居)。

pub mod severity;

use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use chrono::{Duration, NaiveDateTime, Utc};
use duckdb::types::Value as DValue;
use forge::warehouse::Db;
use serde::{Deserialize, Serialize};
use serde_json::json;

use severity::{classify, Direction, Method};

#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    pub metrics: Vec<MetricDef>,
    pub settings: Settings,
}

#[derive(Debug, Clone, Deserialize)]
pub struct MetricDef {
    pub name: String,
    pub targets: Vec<String>,
    #[serde(default)]
    pub method: Method,
    #[serde(default)]
    pub direction: Direction,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Settings {
    pub lookback_days: i64,
    pub min_history: usize,
}

impl Config {
    pub fn load(path: &Path) -> Result<Self> {
        let text = std::fs::read_to_string(path)
            .with_context(|| format!("{} が読めません", path.display()))?;
        serde_yaml::from_str(&text).with_context(|| format!("{} の形式が不正です", path.display()))
    }
}

fn now() -> NaiveDateTime {
    Utc::now().naive_utc()
}

fn ts(t: NaiveDateTime) -> DValue {
    DValue::Text(t.format("%Y-%m-%d %H:%M:%S%.6f").to_string())
}

fn text(s: &str) -> DValue {
    DValue::Text(s.into())
}

/// テーブル名として安全か(`schema.table` の形だけ許す)。
fn safe_relation(t: &str) -> Result<&str> {
    if !t.is_empty()
        && t.split('.')
            .all(|p| !p.is_empty() && p.chars().all(|c| c.is_ascii_alphanumeric() || c == '_'))
    {
        Ok(t)
    } else {
        bail!("監視対象名が不正です: {t}")
    }
}

/// 指標の現在値。取れなければ None(履歴がない等)。
pub fn fetch(db: &Db, metric: &str, target: &str, at: NaiveDateTime) -> Result<Option<f64>> {
    let r = match metric {
        "row_count" => db.query(&format!(
            "select count(*) as v from {}",
            safe_relation(target)?
        ))?,
        // 最後の本番デプロイ成功からの経過分(DuckDB 版では「データ更新時刻」の代わり)
        "freshness_minutes" => db.query(&format!(
            "select date_diff('second', max(deployed_at), cast({} as timestamp)) / 60.0 as v \
             from ops.deployments where status = 'success'",
            forge::warehouse::quote_str(&at.format("%Y-%m-%d %H:%M:%S").to_string())
        ))?,
        "run_seconds" => db.query(&format!(
            "select execution_seconds as v from ops.run_results \
             where target = 'prod' and unique_id = {} order by generated_at desc limit 1",
            forge::warehouse::quote_str(target)
        ))?,
        other => bail!("未対応の指標: {other}"),
    };
    Ok(r.get_f64(0, "v"))
}

/// collect: metrics.yml の指標を取得して ops.metric_snapshots に追記する。
pub fn collect(db: &Db, cfg: &Config) -> Result<usize> {
    let at = now();
    let mut n = 0;
    for m in &cfg.metrics {
        for t in &m.targets {
            let v = match fetch(db, &m.name, t, at) {
                Ok(Some(v)) => v,
                Ok(None) => continue,
                Err(e) => {
                    println!("skip {} {t}: {e:#}", m.name); // テーブル未作成など
                    continue;
                }
            };
            db.execute_with(
                "insert into ops.metric_snapshots values (cast(? as timestamp), ?, ?, ?)",
                vec![ts(at), text(&m.name), text(t), DValue::Double(v)],
            )?;
            println!("collected {:<18} {:<35} {v:.2}", m.name, t);
            n += 1;
        }
    }
    Ok(n)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// 記録のみ(閾値調整期間)
    Shadow,
    /// 段階2以上で診断プロンプトを出力
    Active,
}

impl Mode {
    pub fn as_str(&self) -> &'static str {
        match self {
            Mode::Shadow => "shadow",
            Mode::Active => "active",
        }
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Finding {
    pub metric: String,
    pub target: String,
    pub value: f64,
    pub baseline: Option<f64>,
    pub stage: i32,
    pub reason: String,
    pub last_deploy_sha: Option<String>,
    pub labels: Vec<String>,
}

fn labels(stage: i32) -> Vec<String> {
    match stage {
        2 => vec!["monitor:diagnose".into()],
        _ => vec!["monitor:propose".into(), "needs-approval".into()],
    }
}

/// detect: 最新スナップショットを過去 lookback_days 日と比べて段階判定し、ops.monitor_events に記録する。
pub fn detect(db: &Db, cfg: &Config, mode: Mode) -> Result<Vec<Finding>> {
    let at = now();
    let since = at - Duration::days(cfg.settings.lookback_days);
    let sha = db
        .query("select git_sha from ops.deployments where status = 'success' order by deployed_at desc limit 1")?
        .get_str(0, "git_sha");
    let mut findings = Vec::new();

    for m in &cfg.metrics {
        for t in &m.targets {
            let r = db.query(&format!(
                "select value from ops.metric_snapshots where metric = {} and target = {} \
                 and captured_at >= cast({} as timestamp) order by captured_at",
                forge::warehouse::quote_str(&m.name),
                forge::warehouse::quote_str(t),
                forge::warehouse::quote_str(&since.format("%Y-%m-%d %H:%M:%S").to_string())
            ))?;
            let values: Vec<f64> = (0..r.rows.len())
                .filter_map(|i| r.get_f64(i, "value"))
                .collect();
            let Some((&latest, hist)) = values.split_last() else {
                continue;
            };
            let v = classify(
                hist,
                latest,
                m.method,
                m.direction,
                cfg.settings.min_history,
            );
            let score = v.score.filter(|s| s.is_finite());
            db.execute_with(
                "insert into ops.monitor_events values (cast(? as timestamp), ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                vec![
                    ts(at),
                    text(&m.name),
                    text(t),
                    DValue::Double(latest),
                    v.baseline.map(DValue::Double).unwrap_or(DValue::Null),
                    score.map(DValue::Double).unwrap_or(DValue::Null),
                    DValue::Int(v.stage),
                    text(&v.reason),
                    text(mode.as_str()),
                    sha.as_deref().map(text).unwrap_or(DValue::Null),
                ],
            )?;
            println!("stage={:>2} {:<18} {:<35} {}", v.stage, m.name, t, v.reason);
            if v.stage >= 2 {
                findings.push(Finding {
                    metric: m.name.clone(),
                    target: t.clone(),
                    value: latest,
                    baseline: v.baseline,
                    stage: v.stage,
                    reason: v.reason.clone(),
                    last_deploy_sha: sha.clone(),
                    labels: labels(v.stage),
                });
            }
        }
    }
    Ok(findings)
}

/// active モードで段階2以上があれば、診断プロンプトを書き出してパスを返す。
pub fn write_diagnosis(root: &Path, findings: &[Finding]) -> Result<PathBuf> {
    let base = std::fs::read_to_string(root.join("monitoring/diagnose_prompt.md"))?;
    let prompt = format!(
        "{base}\n\n## findings\n```json\n{}\n```\n",
        serde_json::to_string_pretty(&json!(findings))?
    );
    let dir = root.join("artifacts/diagnose");
    std::fs::create_dir_all(&dir)?;
    let path = dir.join(format!("{}.md", Utc::now().format("%Y%m%dT%H%M%S")));
    std::fs::write(&path, prompt)?;
    Ok(path)
}

/// 決定的な擬似乱数(デモ用。外部クレートを使わない)。
pub struct Rng(u64);

impl Rng {
    pub fn new(seed: u64) -> Self {
        Rng(seed.wrapping_mul(0x9E37_79B9_7F4A_7C15) | 1)
    }
    fn next_f64(&mut self) -> f64 {
        // xorshift64*
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        (self.0.wrapping_mul(0x2545_F491_4F6C_DD1D) >> 11) as f64 / (1u64 << 53) as f64
    }
    /// Box–Muller
    pub fn gauss(&mut self, mu: f64, sd: f64) -> f64 {
        let u1 = self.next_f64().max(f64::MIN_POSITIVE);
        let u2 = self.next_f64();
        mu + sd * (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()
    }
}

/// 監視デモ用: 過去28日分の擬似スナップショット(1日1点)を投入する。
/// anomaly なら最新値に異常(行数3倍)を入れる。
pub fn seed_history(db: &Db, anomaly: bool) -> Result<()> {
    let mut rng = Rng::new(42);
    let at = now();
    let series = [
        ("row_count", "analytics.fct_orders", 10.0, 0.5),
        ("row_count", "analytics.dim_customers", 5.0, 0.3),
        ("run_seconds", "model.sdlc_sample.fct_orders", 0.05, 0.01),
    ];
    db.execute_with(
        "delete from ops.metric_snapshots where captured_at < cast(? as timestamp)",
        vec![ts(at - Duration::minutes(5))],
    )?;
    for (metric, target, mu, sd) in series {
        for d in (1..=28).rev() {
            db.execute_with(
                "insert into ops.metric_snapshots values (cast(? as timestamp), ?, ?, ?)",
                vec![
                    ts(at - Duration::days(d)),
                    text(metric),
                    text(target),
                    DValue::Double(rng.gauss(mu, sd).max(0.0)),
                ],
            )?;
        }
    }
    if anomaly {
        db.execute_with(
            "insert into ops.metric_snapshots values (cast(? as timestamp), ?, ?, ?)",
            vec![
                ts(at),
                text("row_count"),
                text("analytics.fct_orders"),
                DValue::Double(30.0),
            ],
        )?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rng_is_deterministic_and_roughly_normal() {
        let mut a = Rng::new(42);
        let mut b = Rng::new(42);
        let xs: Vec<f64> = (0..2000).map(|_| a.gauss(10.0, 0.5)).collect();
        assert_eq!(xs[0], b.gauss(10.0, 0.5));
        let mean = xs.iter().sum::<f64>() / xs.len() as f64;
        assert!((mean - 10.0).abs() < 0.05, "{mean}");
    }

    #[test]
    fn rejects_unsafe_targets() {
        assert!(safe_relation("analytics.fct_orders").is_ok());
        assert!(safe_relation("analytics.x; drop table y").is_err());
    }
}

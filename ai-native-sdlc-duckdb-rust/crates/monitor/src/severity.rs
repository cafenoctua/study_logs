//! σ段階判定。決定的な純粋関数のみ(DB に触らない)なので cargo test で全部検証できる。
//!
//! | 段階 | 条件(既定) | 動作 |
//! |---|---|---|
//! | -1 | 履歴が min_history 未満 | insufficient_history として記録 |
//! | 1 | |z| ≥ 1σ | ops.monitor_events にログのみ |
//! | 2 | |z| ≥ 2σ | 読み取り専用の診断プロンプト(monitor:diagnose) |
//! | 3 | |z| ≥ 3σ | 診断 + intent.md 形式の対処案(needs-approval)。実行はしない |

use serde::{Deserialize, Serialize};

pub const MAD_SCALE: f64 = 1.4826;
pub const MIN_HISTORY: usize = 14;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Method {
    /// 平均と標準偏差(母標準偏差)
    #[default]
    Zscore,
    /// 中央値と MAD(外れ値や偏りに強い)
    Robust,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Direction {
    #[default]
    Both,
    /// 増えたときだけ異常(鮮度の遅れ、実行時間)
    Up,
    /// 減ったときだけ異常
    Down,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Verdict {
    /// -1 = insufficient_history, 0..=3
    pub stage: i32,
    /// σ 換算の偏差(向き考慮後)。履歴不足は None、一定の履歴から変化したら +∞
    pub score: Option<f64>,
    pub baseline: Option<f64>,
    pub reason: String,
}

fn verdict(
    stage: i32,
    score: Option<f64>,
    baseline: Option<f64>,
    reason: impl Into<String>,
) -> Verdict {
    Verdict {
        stage,
        score,
        baseline,
        reason: reason.into(),
    }
}

fn median(xs: &[f64]) -> f64 {
    let mut v = xs.to_vec();
    v.sort_by(f64::total_cmp);
    let n = v.len();
    if n % 2 == 1 {
        v[n / 2]
    } else {
        (v[n / 2 - 1] + v[n / 2]) / 2.0
    }
}

fn center_spread(history: &[f64], method: Method) -> (f64, f64) {
    match method {
        Method::Zscore => {
            let mean = history.iter().sum::<f64>() / history.len() as f64;
            let var =
                history.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / history.len() as f64;
            (mean, var.sqrt())
        }
        Method::Robust => {
            let med = median(history);
            let dev: Vec<f64> = history.iter().map(|x| (x - med).abs()).collect();
            (med, median(&dev) * MAD_SCALE)
        }
    }
}

pub fn classify(
    history: &[f64],
    value: f64,
    method: Method,
    direction: Direction,
    min_history: usize,
) -> Verdict {
    if history.len() < min_history || history.is_empty() {
        return verdict(-1, None, None, "insufficient_history");
    }
    let (center, spread) = center_spread(history, method);

    if spread == 0.0 {
        if value == center {
            return verdict(0, Some(0.0), Some(center), "constant_history_unchanged");
        }
        let delta = value - center;
        if (direction == Direction::Up && delta < 0.0)
            || (direction == Direction::Down && delta > 0.0)
        {
            return verdict(
                0,
                Some(0.0),
                Some(center),
                "constant_history_ignored_direction",
            );
        }
        return verdict(
            3,
            Some(f64::INFINITY),
            Some(center),
            "constant_history_changed",
        );
    }

    let z = (value - center) / spread;
    let score = match direction {
        Direction::Up => z.max(0.0),
        Direction::Down => (-z).max(0.0),
        Direction::Both => z.abs(),
    };
    let stage = if score >= 3.0 {
        3
    } else if score >= 2.0 {
        2
    } else if score >= 1.0 {
        1
    } else {
        0
    };
    let name = match method {
        Method::Zscore => "zscore",
        Method::Robust => "robust",
    };
    verdict(stage, Some(score), Some(center), format!("{name}:{z:+.2}"))
}

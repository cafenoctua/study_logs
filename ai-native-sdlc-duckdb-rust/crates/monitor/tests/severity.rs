//! PR #38 の tests/test_severity.py をそのまま移したもの。
//! `crates/*/tests/` に置いているので LOCK_TESTS=1 で編集を保護できる。
use monitor::severity::*;

const BASE: [f64; 14] = [
    100.0, 101.0, 99.0, 100.0, 102.0, 98.0, 100.0, 101.0, 99.0, 100.0, 100.0, 101.0, 99.0, 100.0,
];

fn c(h: &[f64], v: f64) -> Verdict {
    classify(h, v, Method::Zscore, Direction::Both, MIN_HISTORY)
}

#[test]
fn insufficient_history() {
    let v = c(&BASE[..13], 500.0);
    assert_eq!(v.stage, -1);
    assert_eq!(v.reason, "insufficient_history");
}

#[test]
fn normal_value_is_stage0() {
    assert_eq!(c(&BASE, 100.5).stage, 0);
}

#[test]
fn stages_increase_with_deviation() {
    let stages: Vec<i32> = [100.0, 102.0, 103.0, 105.0]
        .iter()
        .map(|x| c(&BASE, *x).stage)
        .collect();
    let mut sorted = stages.clone();
    sorted.sort();
    assert_eq!(stages, sorted);
    assert_eq!(*stages.last().unwrap(), 3);
}

#[test]
fn direction_up_ignores_drop() {
    assert_eq!(
        classify(&BASE, 50.0, Method::Zscore, Direction::Up, 14).stage,
        0
    );
    assert_eq!(
        classify(&BASE, 150.0, Method::Zscore, Direction::Up, 14).stage,
        3
    );
}

#[test]
fn direction_down_ignores_rise() {
    assert_eq!(
        classify(&BASE, 150.0, Method::Zscore, Direction::Down, 14).stage,
        0
    );
}

#[test]
fn constant_history_changed_is_stage3() {
    let v = c(&[10.0; 14], 11.0);
    assert_eq!(v.stage, 3);
    assert!(v.score.unwrap().is_infinite());
}

#[test]
fn constant_history_unchanged_is_stage0() {
    assert_eq!(c(&[10.0; 14], 10.0).stage, 0);
}

#[test]
fn robust_survives_single_outlier_where_zscore_misses() {
    let mut hist = BASE[..13].to_vec();
    hist.push(10_000.0); // 履歴に外れ値1件
    assert_eq!(
        classify(&hist, 110.0, Method::Zscore, Direction::Both, 14).stage,
        0
    ); // σ が膨らみ見逃す
    assert_eq!(
        classify(&hist, 110.0, Method::Robust, Direction::Both, 14).stage,
        3
    ); // 中央値+MAD なら検知
}

#[test]
fn reason_shows_signed_z() {
    assert!(c(&BASE, 105.0).reason.starts_with("zscore:+"));
}

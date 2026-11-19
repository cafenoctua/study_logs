//! 実際の DuckDB ファイルで collect → detect を通す。

use forge::warehouse::Db;
use monitor::{Config, Mode};

fn setup() -> (tempfile::TempDir, Db) {
    let dir = tempfile::tempdir().unwrap();
    let db = Db::open_path(&dir.path().join("prod.duckdb"), false).unwrap();
    forge::ops::init(&db).unwrap();
    db.execute("create schema analytics; create table analytics.fct_orders as select range as id from range(10)")
        .unwrap();
    (dir, db)
}

fn cfg() -> Config {
    serde_yaml::from_str(
        r#"
metrics:
  - name: row_count
    targets: [analytics.fct_orders, analytics.missing_table]
    method: zscore
    direction: both
  - name: freshness_minutes
    targets: [analytics.fct_orders]
    method: robust
    direction: up
settings: { lookback_days: 28, min_history: 14 }
"#,
    )
    .unwrap()
}

#[test]
fn seed_history_with_anomaly_reaches_stage3() {
    let (_d, db) = setup();
    monitor::seed_history(&db, true).unwrap();
    let f = monitor::detect(&db, &cfg(), Mode::Active).unwrap();
    assert_eq!(f.len(), 1);
    assert_eq!(f[0].target, "analytics.fct_orders");
    assert_eq!(f[0].stage, 3);
    assert_eq!(f[0].labels, vec!["monitor:propose", "needs-approval"]);
    let r = db
        .query("select stage, mode from ops.monitor_events")
        .unwrap();
    assert_eq!(r.get_f64(0, "stage"), Some(3.0));
    assert_eq!(r.get_str(0, "mode").as_deref(), Some("active"));
}

#[test]
fn collect_skips_missing_tables_and_empty_metrics() {
    let (_d, db) = setup();
    // テーブルが無い target と、デプロイ履歴が無い freshness は飛ばす
    assert_eq!(monitor::collect(&db, &cfg()).unwrap(), 1);
    db.execute("insert into ops.deployments values (now()::timestamp - interval 90 minute, 'abc', 'me', 'success')")
        .unwrap();
    assert_eq!(monitor::collect(&db, &cfg()).unwrap(), 2);
    // 履歴が1点しかないので insufficient_history(-1)
    monitor::detect(&db, &cfg(), Mode::Shadow).unwrap();
    let r = db
        .query("select min(stage) as s, any_value(last_deploy_sha) as sha from ops.monitor_events")
        .unwrap();
    assert_eq!(r.get_f64(0, "s"), Some(-1.0));
    assert_eq!(r.get_str(0, "sha").as_deref(), Some("abc"));
}

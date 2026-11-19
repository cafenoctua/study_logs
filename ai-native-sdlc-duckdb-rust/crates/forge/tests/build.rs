//! 実際の DuckDB ファイルでサンプルプロジェクトを build する結合テスト。

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use forge::config::Target;
use forge::project::Project;
use forge::runner::{Command, RunResults, Runner, Status};
use forge::state::{self, Manifest};
use forge::warehouse::Db;

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// サンプル(models / seeds / 設定)を一時ディレクトリに複製する。
fn sandbox() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    for sub in ["models", "seeds"] {
        copy_dir(&repo_root().join(sub), &dir.path().join(sub));
    }
    for f in ["forge_project.toml", "profiles.toml"] {
        std::fs::copy(repo_root().join(f), dir.path().join(f)).unwrap();
    }
    dir
}

fn target(root: &Path, name: &str) -> Target {
    Target::load(root, "sdlc_sample", Some(name), |k| {
        (k == "PR_NUMBER").then(|| "7".to_string())
    })
    .unwrap()
}

fn build(
    root: &Path,
    tname: &str,
    select: &[&str],
    state_dir: Option<&Path>,
) -> (RunResults, Project) {
    let project = Project::load(root).unwrap();
    let t = target(root, tname);
    let manifest = state_dir.and_then(|d| Manifest::load_opt(d).unwrap());
    let sel: Vec<String> = select.iter().map(|s| s.to_string()).collect();
    let selected = forge::select::select(&project, &sel, manifest.as_ref()).unwrap();
    let rels = state::resolve_relations(&project, &t, &selected, manifest.as_ref());
    let db = Db::open_target(&t, &[&t.schema, "raw"]).unwrap();
    let runner = Runner {
        project: &project,
        db: &db,
        target: &t,
        relations: &rels,
        full_refresh: false,
        verbose: false,
    };
    let res = runner.execute(Command::Build, &selected).unwrap();
    Manifest::build(&project, &t)
        .write(&project.target_dir())
        .unwrap();
    (res, project)
}

fn statuses(r: &RunResults) -> Vec<(String, Status)> {
    r.results
        .iter()
        .map(|x| (x.name.clone(), x.status))
        .collect()
}

#[test]
fn dev_build_creates_everything_and_passes_tests() {
    let dir = sandbox();
    let (res, _) = build(dir.path(), "dev", &[], None);
    assert!(!res.has_failures(), "{:#?}", statuses(&res));
    // seed 2 + model 4 + test 12
    assert_eq!(
        res.results
            .iter()
            .filter(|r| r.resource_type == "test")
            .count(),
        12
    );
    assert_eq!(res.results.len(), 18);

    let db = Db::open_path(&dir.path().join("warehouse/dev.duckdb"), true).unwrap();
    let r = db.query("select customer_id, lifetime_value, completed_orders from analytics.dim_customers order by 1").unwrap();
    assert_eq!(r.rows.len(), 5);
    assert_eq!(
        r.get_f64(0, "lifetime_value"),
        Some(2600.0),
        "Alice は completed の 1200 + 800 + 600"
    );
    let kinds = db
        .query("select table_name, table_type from information_schema.tables where table_schema in ('analytics', 'raw') order by 1")
        .unwrap();
    let k: Vec<_> = (0..kinds.rows.len())
        .map(|i| {
            (
                kinds.get_str(i, "table_name").unwrap(),
                kinds.get_str(i, "table_type").unwrap(),
            )
        })
        .collect();
    assert!(k.contains(&("stg_orders".into(), "VIEW".into())));
    assert!(k.contains(&("fct_orders".into(), "BASE TABLE".into())));
    assert!(k.contains(&("raw_orders".into(), "BASE TABLE".into())));
}

/// Slim CI: 本番と比べて変わったモデル+下流だけを ci.duckdb に作り、上流は attach した prod を読む。
#[test]
fn slim_ci_builds_only_modified_and_defers_to_prod() {
    let dir = sandbox();
    let root = dir.path();
    let (prod, _) = build(root, "prod", &[], None);
    assert!(!prod.has_failures());
    let state_dir = root.join("artifacts/prod-manifest");
    std::fs::create_dir_all(&state_dir).unwrap();
    std::fs::copy(
        root.join("forge_target/manifest.json"),
        state_dir.join("manifest.json"),
    )
    .unwrap();

    // fct_orders だけ変更
    let f = root.join("models/marts/fct_orders.sql");
    let s = std::fs::read_to_string(&f)
        .unwrap()
        .replace("o.amount,", "o.amount * 1 as amount,");
    std::fs::write(&f, s).unwrap();

    let (ci, project) = build(root, "ci", &["state:modified+"], Some(&state_dir));
    assert!(!ci.has_failures(), "{:#?}", statuses(&ci));
    let built: BTreeSet<String> = ci
        .results
        .iter()
        .filter(|r| r.resource_type == "model")
        .map(|r| r.name.clone())
        .collect();
    assert_eq!(
        built,
        ["dim_customers", "fct_orders"].map(String::from).into()
    );

    // ci.duckdb には変更分だけがあり、stg / seed は無い(本番を参照した)
    let t = target(root, "ci");
    let db = Db::open_target(&t, &[]).unwrap();
    let r = db
        .query("select table_name from information_schema.tables where table_catalog = 'ci' order by 1")
        .unwrap();
    let names: Vec<_> = (0..r.rows.len())
        .filter_map(|i| r.get_str(i, "table_name"))
        .collect();
    assert_eq!(names, vec!["dim_customers", "fct_orders"]);
    let rels = state::resolve_relations(
        &project,
        &t,
        &built,
        Manifest::load_opt(&state_dir).unwrap().as_ref(),
    );
    assert_eq!(rels["stg_orders"].to_string(), "prod.analytics.stg_orders");
    assert_eq!(
        rels["fct_orders"].to_string(),
        "ci.analytics_ci_pr7.fct_orders"
    );
}

#[test]
fn failing_test_skips_downstream() {
    let dir = sandbox();
    // accepted_values を壊す(refunded を許可しない)
    let y = dir.path().join("models/staging/schema.yml");
    let s = std::fs::read_to_string(&y)
        .unwrap()
        .replace("[completed, cancelled, refunded]", "[completed, cancelled]");
    std::fs::write(&y, s).unwrap();
    let (res, _) = build(dir.path(), "dev", &[], None);
    let st = statuses(&res);
    assert!(
        st.contains(&("accepted_values_stg_orders_status".into(), Status::Fail)),
        "{st:#?}"
    );
    assert!(st.contains(&("fct_orders".into(), Status::Skipped)));
    assert!(st.contains(&("dim_customers".into(), Status::Skipped)));
}

#[test]
fn incremental_delete_insert() {
    let dir = sandbox();
    let f = dir.path().join("models/marts/fct_orders.sql");
    let s = std::fs::read_to_string(&f).unwrap();
    let inc = format!(
        "{{{{ config(materialized='incremental', unique_key='order_id') }}}}\n{}\n{{% if is_incremental() %}}where o.ordered_at >= (select max(ordered_at) - interval 3 day from {{{{ this }}}}){{% endif %}}\n",
        s.trim_end()
    );
    std::fs::write(&f, inc).unwrap();
    let (first, _) = build(dir.path(), "dev", &["+fct_orders"], None);
    assert!(!first.has_failures(), "{:#?}", statuses(&first));
    let (second, _) = build(dir.path(), "dev", &["fct_orders"], None);
    assert!(!second.has_failures(), "{:#?}", statuses(&second));
    assert!(second.results[0]
        .message
        .as_deref()
        .unwrap()
        .starts_with("delete+insert"));
    let db = Db::open_path(&dir.path().join("warehouse/dev.duckdb"), true).unwrap();
    let r = db
        .query("select count(*) as n, count(distinct order_id) as d from analytics.fct_orders")
        .unwrap();
    assert_eq!(r.get_f64(0, "n"), r.get_f64(0, "d"), "重複しない");
    assert_eq!(r.get_f64(0, "n"), Some(10.0));
}

#[test]
fn sample_is_bigquery_compatible_and_renders_for_lint() {
    let project = Project::load(&repo_root()).unwrap();
    assert_eq!(forge::bqcheck::check_project(&project).unwrap(), vec![]);
    let dir = sandbox();
    let p = Project::load(dir.path()).unwrap();
    let files = forge::lint::render_for_lint(&p, &[]).unwrap();
    assert_eq!(files.len(), 4);
    let sql = std::fs::read_to_string(
        files
            .iter()
            .find(|f| f.ends_with("models/marts/dim_customers.sql"))
            .unwrap(),
    )
    .unwrap();
    assert!(sql.contains("from lint.analytics.fct_orders"));
}

#[test]
fn selectors() {
    let project = Project::load(&repo_root()).unwrap();
    let s = |e: &str| forge::select::select(&project, &[e.to_string()], None).unwrap();
    assert_eq!(
        s("stg_orders+"),
        ["dim_customers", "fct_orders", "stg_orders"]
            .map(String::from)
            .into()
    );
    assert_eq!(s("+fct_orders").len(), 3);
    assert_eq!(s("path:models/staging").len(), 2);
    assert!(forge::select::select(&project, &["state:modified".into()], None).is_err());
}

fn copy_dir(from: &Path, to: &Path) {
    for e in walkdir::WalkDir::new(from) {
        let e = e.unwrap();
        let dest = to.join(e.path().strip_prefix(from).unwrap());
        if e.file_type().is_dir() {
            std::fs::create_dir_all(&dest).unwrap();
        } else {
            std::fs::copy(e.path(), &dest).unwrap();
        }
    }
}

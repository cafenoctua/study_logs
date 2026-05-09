use dbt_impact::graph::DependencyGraph;
use dbt_impact::manifest::Manifest;
use std::path::Path;

#[test]
fn test_load_manifest_success() {
    let result = Manifest::load(Path::new("manifest.json"));
    assert!(result.is_ok());
}

#[test]
fn test_load_manifest_not_found() {
    let result = Manifest::load(Path::new("not_exist.json"));
    assert!(result.is_err());
}

#[test]
fn test_downstream_with_real_manifest() {
    let manifest = Manifest::load(Path::new("manifest.json")).unwrap();
    let graph = DependencyGraph::from_manifest(&manifest);
    let result = graph.downstream("stg_ga_sample", None);
    assert!(!result.is_empty());
}

#[test]
fn test_upstream_with_real_manifest() {
    let manifest = Manifest::load(Path::new("manifest.json")).unwrap();
    let graph = DependencyGraph::from_manifest(&manifest);
    let result = graph.upstream("stg_ga_sample", None);
    assert!(!result.is_empty());
}

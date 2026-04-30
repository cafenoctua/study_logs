mod graph;
mod manifest;
use std::path::Path;

use graph::DependencyGraph;
use manifest::Manifest;

fn main() {
    let path = Path::new("manifest.json");
    let manifest = Manifest::load(path).unwrap();
    print!("{:?}\n", manifest.nodes.len());

    let graph = DependencyGraph::from_manifest(&manifest);
    let result = graph.downstream("stg_ga_sample", None);
    println!("{:?}\n", result);

    let result = graph.upstream("fct_visits", None);
    println!("{:?}\n", result);
}

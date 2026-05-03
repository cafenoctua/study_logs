mod graph;
mod manifest;
mod output;

use std::path::Path;

use clap::{Parser, Subcommand};
use graph::DependencyGraph;
use manifest::Manifest;

use crate::output::{Formatter, JsonFormatter, ListFormatter, TreeFormatter};

#[derive(Parser)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Downstream {
        model: String,
        #[arg(long)]
        depth: Option<usize>,
        #[arg(long, default_value = "manifest.json")]
        manifest: String,
        #[arg(long, default_value = "list")]
        format: String, // "list" / "tree" / "json"
    },

    Upstream {
        model: String,
        #[arg(long)]
        depth: Option<usize>,
        #[arg(long, default_value = "manifest.json")]
        manifest: String,
        #[arg(long, default_value = "list")]
        format: String, // "list" / "tree" / "json"
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Downstream {
            model,
            depth,
            manifest,
            format,
        } => {
            let path = Path::new(&manifest);
            let manifest = Manifest::load(path).unwrap();
            let graph = DependencyGraph::from_manifest(&manifest);
            let result = graph.downstream(&model, depth);
            let formatter: Box<dyn Formatter> = match format.as_str() {
                "tree" => Box::new(TreeFormatter),
                "json" => Box::new(JsonFormatter),
                _ => Box::new(ListFormatter),
            };
            print!("{}", formatter.format(&model, &result));
        }

        Commands::Upstream {
            model,
            depth,
            manifest,
            format,
        } => {
            let path = Path::new(&manifest);
            let manifest = Manifest::load(path).unwrap();
            let graph = DependencyGraph::from_manifest(&manifest);
            let result = graph.upstream(&model, depth);
            let formatter: Box<dyn Formatter> = match format.as_str() {
                "tree" => Box::new(TreeFormatter),
                "json" => Box::new(JsonFormatter),
                _ => Box::new(ListFormatter),
            };
            print!("{}", formatter.format(&model, &result));
        }
    }
}

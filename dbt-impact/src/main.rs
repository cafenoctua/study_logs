mod graph;
mod manifest;
use std::path::Path;

use clap::{Parser, Subcommand};
use graph::DependencyGraph;
use manifest::Manifest;

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
    },

    Upstream {
        model: String,
        #[arg(long)]
        depth: Option<usize>,
        #[arg(long, default_value = "manifest.json")]
        manifest: String,
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Downstream {
            model,
            depth,
            manifest,
        } => {
            let path = Path::new(&manifest);
            let manifest = Manifest::load(path).unwrap();
            let graph = DependencyGraph::from_manifest(&manifest);
            let result = graph.downstream(&model, depth);
            print!("{:?}", result);
        }

        Commands::Upstream {
            model,
            depth,
            manifest,
        } => {
            let path = Path::new(&manifest);
            let manifest = Manifest::load(path).unwrap();
            let graph = DependencyGraph::from_manifest(&manifest);
            let result = graph.upstream(&model, depth);
            print!("{:?}", result);
        }
    }
}

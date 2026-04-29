use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Deserialize)]
pub struct Manifest {
    pub nodes: HashMap<String, Node>,
    pub sources: HashMap<String, Source>,
    pub parent_map: HashMap<String, Vec<String>>,
    pub child_map: HashMap<String, Vec<String>>,
}

#[derive(Debug, Deserialize)]
pub struct Node {
    unique_id: String,
    name: String,
    resource_type: String,
}

#[derive(Debug, Deserialize)]
pub struct Source {
    unique_id: String,
    name: String,
    resource_type: String,
}

impl Manifest {
    pub fn load(path: &Path) -> Result<Manifest, Box<dyn std::error::Error>> {
        let file = std::fs::File::open(path)?;
        let manifest = serde_json::from_reader(file)?;
        Ok(manifest)
    }
}

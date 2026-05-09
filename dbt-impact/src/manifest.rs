use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;

use crate::error::ImpactError;

#[derive(Debug, Deserialize)]
pub struct Manifest {
    pub nodes: HashMap<String, Node>,
    pub sources: HashMap<String, Source>,
    pub parent_map: HashMap<String, Vec<String>>,
    pub child_map: HashMap<String, Vec<String>>,
}

#[derive(Debug, Deserialize, Clone)]
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
    pub fn load(path: &Path) -> Result<Manifest, ImpactError> {
        let file = std::fs::File::open(path)
            .map_err(|_| ImpactError::ManifestNotFound(path.to_path_buf()))?;
        let manifest = serde_json::from_reader(file)?;
        Ok(manifest)
    }
}

#[cfg(test)]
impl Node {
    pub fn new(unique_id: &str, name: &str, resource_type: &str) -> Self {
        Self {
            unique_id: unique_id.to_string(),
            name: name.to_string(),
            resource_type: resource_type.to_string(),
        }
    }
}

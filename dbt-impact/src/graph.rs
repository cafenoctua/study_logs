use crate::{
    error::ImpactError,
    manifest::{Manifest, Node},
};
use std::collections::HashMap;

#[derive(Debug)]
pub struct DependencyGraph {
    nodes: HashMap<String, Node>,
    parent_map: HashMap<String, Vec<String>>,
    child_map: HashMap<String, Vec<String>>,
}

impl DependencyGraph {
    pub fn from_manifest(manifest: &Manifest) -> Self {
        Self {
            nodes: manifest.nodes.clone(),
            parent_map: manifest.parent_map.clone(),
            child_map: manifest.child_map.clone(),
        }
    }

    fn resolve_node_id(&self, name: &str) -> Result<String, ImpactError> {
        self.nodes
            .keys()
            .filter(|k| k.ends_with(&format!(".{}", name)))
            .next()
            .cloned()
            .ok_or_else(|| ImpactError::ModelNotFound(name.to_string()))
    }

    fn bfs(
        &self,
        name: &str,
        depth: Option<usize>,
        map: &HashMap<String, Vec<String>>,
    ) -> Vec<(String, usize)> {
        use std::collections::{HashSet, VecDeque};

        let root = match self.resolve_node_id(&name) {
            Ok(id) => id,
            Err(e) => {
                eprintln!("エラー: {}", e);
                std::process::exit(1);
            }
        };

        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        let mut result = vec![];

        queue.push_back((root.to_string(), 0));

        while let Some((node, d)) = queue.pop_front() {
            if visited.contains(&node) {
                continue;
            }
            visited.insert(node.clone());
            result.push((node.clone(), d));

            // depth 制限チェック
            if let Some(max) = depth {
                if d >= max {
                    continue;
                }
            }

            // mapから次のノードを取得してqueueに積む
            if let Some(elements) = map.get(&node) {
                for element in elements {
                    queue.push_back((element.clone(), d + 1));
                }
            }
        }

        result
    }

    pub fn downstream(&self, root: &str, depth: Option<usize>) -> Vec<(String, usize)> {
        self.bfs(root, depth, &self.child_map)
    }

    pub fn upstream(&self, root: &str, depth: Option<usize>) -> Vec<(String, usize)> {
        self.bfs(root, depth, &self.parent_map)
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::manifest::{Manifest, Node};
    use std::collections::HashMap;

    fn make_manifest() -> Manifest {
        let mut nodes = HashMap::new();
        nodes.insert(
            "model.project.model_a".to_string(),
            Node::new("model.project_id.model_a", "model_a", "model"),
        );
        nodes.insert(
            "model.project.model_b".to_string(),
            Node::new("model.project_id.model_b", "model_b", "model"),
        );

        let mut child_map = HashMap::new();
        child_map.insert(
            "model.project.model_a".to_string(),
            vec!["model.project.model_b".to_string()],
        );
        let mut parent_map = HashMap::new();
        parent_map.insert(
            "model.project.model_b".to_string(),
            vec!["model.project.model_a".to_string()],
        );
        Manifest {
            nodes,
            sources: HashMap::new(),
            parent_map,
            child_map,
        }
    }

    #[test]
    fn test_resolve_found() {
        let graph = DependencyGraph::from_manifest(&make_manifest());
        assert!(graph.resolve_node_id("model_a").is_ok());
    }

    #[test]
    fn test_resolve_not_found() {
        let graph = DependencyGraph::from_manifest(&make_manifest());
        assert!(graph.resolve_node_id("not_exist").is_err());
    }

    #[test]
    fn test_downstream_root_depth() {
        let graph = DependencyGraph::from_manifest(&make_manifest());
        let result = graph.downstream("model_a", None);
        assert_eq!(result[0].1, 0);
    }

    #[test]
    fn test_downstream_depth_limit() {
        let graph = DependencyGraph::from_manifest(&make_manifest());
        let result = graph.downstream("model_b", Some(1));
        assert_eq!(result.len(), 1);
    }

    #[test]
    fn test_upstream_root_depth() {
        let graph = DependencyGraph::from_manifest(&make_manifest());
        let result = graph.upstream("model_b", None);
        assert_eq!(result[0].1, 0);
    }
}

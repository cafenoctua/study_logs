// mod manifest {
//     use Manifest;
// }
use crate::manifest::{Manifest, Node};
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

    fn resolve_node_id(&self, name: &str, nodes: &HashMap<String, Node>) -> Option<String> {
        nodes
            .keys()
            .filter(|k| k.ends_with(&format!(".{}", name)))
            .next()
            .cloned()
    }

    fn bfs(
        &self,
        name: &str,
        depth: Option<usize>,
        map: &HashMap<String, Vec<String>>,
    ) -> Vec<(String, usize)> {
        use std::collections::{HashSet, VecDeque};

        let root = match self.resolve_node_id(&name, &self.nodes) {
            Some(id) => id,
            None => return vec![],
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

// mod manifest {
//     use Manifest;
// }
use crate::manifest::Manifest;
use std::collections::HashMap;

#[derive(Debug)]
pub struct DependencyGraph {
    parent_map: HashMap<String, Vec<String>>,
    child_map: HashMap<String, Vec<String>>,
}

impl DependencyGraph {
    pub fn from_manifest(manifest: &Manifest) -> Self {
        Self {
            parent_map: manifest.parent_map.clone(),
            child_map: manifest.child_map.clone(),
        }
    }

    fn bfs(
        &self,
        root: &str,
        depth: Option<usize>,
        map: &HashMap<String, Vec<String>>,
    ) -> Vec<(String, usize)> {
        use std::collections::{HashSet, VecDeque};

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

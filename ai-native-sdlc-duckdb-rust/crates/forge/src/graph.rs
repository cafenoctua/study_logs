//! モデル間の依存グラフ(DAG)。

use std::collections::{BTreeMap, BTreeSet, VecDeque};

use anyhow::{bail, Result};

#[derive(Debug, Default, Clone)]
pub struct Graph {
    parents: BTreeMap<String, BTreeSet<String>>,
    children: BTreeMap<String, BTreeSet<String>>,
}

impl Graph {
    /// `deps`: ノード名 → そのノードが参照するノード名
    pub fn new(deps: &BTreeMap<String, BTreeSet<String>>) -> Result<Self> {
        let mut g = Graph::default();
        for (node, ps) in deps {
            g.parents.entry(node.clone()).or_default();
            g.children.entry(node.clone()).or_default();
            for p in ps {
                if !deps.contains_key(p) {
                    bail!("{node} が存在しないモデル {p} を参照しています");
                }
                g.parents.get_mut(node).unwrap().insert(p.clone());
                g.children
                    .entry(p.clone())
                    .or_default()
                    .insert(node.clone());
            }
        }
        g.topo_order()?; // 循環チェック
        Ok(g)
    }

    pub fn nodes(&self) -> impl Iterator<Item = &String> {
        self.parents.keys()
    }

    pub fn parents(&self, n: &str) -> &BTreeSet<String> {
        static EMPTY: BTreeSet<String> = BTreeSet::new();
        self.parents.get(n).unwrap_or(&EMPTY)
    }

    /// 全ノードのトポロジカル順(同順位は名前順で決定的)。
    pub fn topo_order(&self) -> Result<Vec<String>> {
        let all: BTreeSet<String> = self.parents.keys().cloned().collect();
        let waves = self.waves(&all)?;
        Ok(waves.into_iter().flatten().collect())
    }

    /// `subset` だけを対象に、並列実行できる段(wave)に分ける。
    /// subset 外のノードを経由した間接依存も順序に反映する。
    pub fn waves(&self, subset: &BTreeSet<String>) -> Result<Vec<Vec<String>>> {
        let mut indeg: BTreeMap<&String, usize> = BTreeMap::new();
        let mut edges: BTreeMap<&String, BTreeSet<&String>> = BTreeMap::new();
        for n in subset {
            indeg.entry(n).or_insert(0);
        }
        for n in subset {
            for a in self.ancestors(n) {
                if let Some(a_ref) = subset.get(&a) {
                    if edges.entry(a_ref).or_default().insert(n) {
                        *indeg.get_mut(n).unwrap() += 1;
                    }
                }
            }
        }
        let mut waves = Vec::new();
        let mut ready: Vec<&String> = indeg
            .iter()
            .filter(|(_, d)| **d == 0)
            .map(|(n, _)| *n)
            .collect();
        let mut done = 0;
        while !ready.is_empty() {
            ready.sort();
            let mut next = Vec::new();
            for n in &ready {
                for c in edges.get(n).into_iter().flatten() {
                    let d = indeg.get_mut(c).unwrap();
                    *d -= 1;
                    if *d == 0 {
                        next.push(*c);
                    }
                }
            }
            done += ready.len();
            waves.push(ready.iter().map(|s| s.to_string()).collect());
            ready = next;
        }
        if done != subset.len() {
            let stuck: Vec<_> = indeg
                .iter()
                .filter(|(_, d)| **d > 0)
                .map(|(n, _)| n.as_str())
                .collect();
            bail!("依存関係が循環しています: {}", stuck.join(", "));
        }
        Ok(waves)
    }

    fn walk(&self, start: &str, next: &BTreeMap<String, BTreeSet<String>>) -> BTreeSet<String> {
        let mut seen = BTreeSet::new();
        let mut q: VecDeque<&str> = next
            .get(start)
            .into_iter()
            .flatten()
            .map(|s| s.as_str())
            .collect();
        while let Some(n) = q.pop_front() {
            if seen.insert(n.to_string()) {
                q.extend(next.get(n).into_iter().flatten().map(|s| s.as_str()));
            }
        }
        seen
    }

    pub fn ancestors(&self, n: &str) -> BTreeSet<String> {
        self.walk(n, &self.parents)
    }

    pub fn descendants(&self, n: &str) -> BTreeSet<String> {
        self.walk(n, &self.children)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn g(edges: &[(&str, &[&str])]) -> Result<Graph> {
        let deps = edges
            .iter()
            .map(|(n, ps)| (n.to_string(), ps.iter().map(|p| p.to_string()).collect()))
            .collect();
        Graph::new(&deps)
    }

    #[test]
    fn orders_and_waves() {
        let g = g(&[("a", &[]), ("b", &["a"]), ("c", &["a"]), ("d", &["b", "c"])]).unwrap();
        assert_eq!(g.topo_order().unwrap(), vec!["a", "b", "c", "d"]);
        assert_eq!(g.descendants("a").len(), 3);
        assert_eq!(g.ancestors("d").len(), 3);
        // b を除いても a → d の順序は保つ
        let subset = ["a", "d"].iter().map(|s| s.to_string()).collect();
        assert_eq!(g.waves(&subset).unwrap(), vec![vec!["a"], vec!["d"]]);
    }

    #[test]
    fn detects_cycles_and_missing() {
        assert!(g(&[("a", &["b"]), ("b", &["a"])]).is_err());
        assert!(g(&[("a", &["zzz"])]).is_err());
    }
}

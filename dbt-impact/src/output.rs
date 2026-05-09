pub struct ListFormatter;
pub struct TreeFormatter;

pub trait Formatter {
    fn format(&self, root: &str, nodes: &[(String, usize)]) -> String;
}

impl Formatter for ListFormatter {
    fn format(&self, _root: &str, nodes: &[(String, usize)]) -> String {
        // ノードIDを1行ずつ並べる
        nodes
            .iter()
            .map(|(id, _)| id.as_str())
            .collect::<Vec<_>>()
            .join("\n")
    }
}

impl Formatter for TreeFormatter {
    fn format(&self, _root: &str, nodes: &[(String, usize)]) -> String {
        let max_depth = nodes.iter().map(|(_, d)| *d).max().unwrap_or(0);
        let mut has_sibling_at = vec![false; max_depth + 1];
        let mut lines = vec![];

        for (i, (id, depth)) in nodes.iter().enumerate() {
            let is_last = !nodes[i + 1..]
                .iter()
                .take_while(|(_, d)| *d >= *depth)
                .any(|(_, next_depth)| *next_depth == *depth);

            has_sibling_at[*depth] = !is_last;

            let prefix: String = (0..*depth)
                .map(|d| {
                    if d + 1 == *depth {
                        if is_last {
                            "└── "
                        } else {
                            "├── "
                        }
                    } else {
                        if has_sibling_at[d + 1] {
                            "│   "
                        } else {
                            "    "
                        }
                    }
                })
                .collect();
            lines.push(format!("{}{}", prefix, id));
        }

        lines.join("\n")
    }
}

pub struct JsonFormatter;

impl Formatter for JsonFormatter {
    fn format(&self, _root: &str, nodes: &[(String, usize)]) -> String {
        // serde_json::to_string で Vec<String> を JSON配列に変換
        let ids: Vec<&str> = nodes.iter().map(|(id, _)| id.as_str()).collect();
        serde_json::to_string_pretty(&ids).unwrap()
    }
}

#[cfg(test)]
mod test {
    use super::*;

    fn sample_nodes() -> Vec<(String, usize)> {
        vec![
            ("model.project.root".to_string(), 0),
            ("model.project.child_a".to_string(), 1),
            ("model.project.child_b".to_string(), 1),
        ]
    }

    #[test]
    fn test_list_contains_all_nodes() {
        let output = ListFormatter.format("root", &sample_nodes());
        assert!(output.contains("model.project.child_a"));
        assert!(output.contains("model.project.child_b"));
    }

    #[test]
    fn test_tree_symbol() {
        let output = TreeFormatter.format("root", &sample_nodes());
        assert!(output.contains("├──"));
        assert!(output.contains("└──"));
    }

    #[test]
    fn test_tree_last_node_uses_end_symbol() {
        let output = TreeFormatter.format("root", &sample_nodes());
        let last_line = output.lines().last().unwrap();
        assert!(last_line.contains("└──"));
    }

    #[test]
    fn test_json_is_array() {
        let output = JsonFormatter.format("root", &sample_nodes());
        let first_line = output.lines().next().unwrap();
        let last_line = output.lines().last().unwrap();
        assert!(first_line.contains("["));
        assert!(last_line.contains("]"));
    }
}

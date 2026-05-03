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

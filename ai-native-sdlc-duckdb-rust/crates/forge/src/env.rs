//! 設定ファイル中の `${VAR}` / `${VAR:-default}` を環境変数で展開する。

use anyhow::{bail, Result};

pub fn expand(input: &str) -> Result<String> {
    expand_with(input, |k| std::env::var(k).ok())
}

pub fn expand_with(input: &str, lookup: impl Fn(&str) -> Option<String>) -> Result<String> {
    let mut out = String::with_capacity(input.len());
    let mut rest = input;
    while let Some(start) = rest.find("${") {
        out.push_str(&rest[..start]);
        let after = &rest[start + 2..];
        let Some(end) = after.find('}') else {
            bail!("閉じていない ${{ があります: {input}");
        };
        let expr = &after[..end];
        let (name, default) = match expr.split_once(":-") {
            Some((n, d)) => (n, Some(d)),
            None => (expr, None),
        };
        match lookup(name).filter(|v| !v.is_empty()) {
            Some(v) => out.push_str(&v),
            None => match default {
                Some(d) => out.push_str(d),
                None => bail!("環境変数 {name} が設定されていません"),
            },
        }
        rest = &after[end + 1..];
    }
    out.push_str(rest);
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lookup(k: &str) -> Option<String> {
        match k {
            "P" => Some("proj".into()),
            "EMPTY" => Some(String::new()),
            _ => None,
        }
    }

    #[test]
    fn expands_vars_and_defaults() {
        assert_eq!(expand_with("a_${P}_b", lookup).unwrap(), "a_proj_b");
        assert_eq!(expand_with("${NOPE:-me}", lookup).unwrap(), "me");
        assert_eq!(expand_with("${EMPTY:-x}", lookup).unwrap(), "x");
        assert_eq!(expand_with("plain", lookup).unwrap(), "plain");
    }

    #[test]
    fn missing_without_default_is_error() {
        assert!(expand_with("${NOPE}", lookup).is_err());
        assert!(expand_with("${P", lookup).is_err());
    }
}

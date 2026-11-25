//! モデル SQL のテンプレート(Jinja 互換: minijinja)。
//!
//! 使える関数・変数:
//! - `{{ ref('model') }}` / `{{ source('src', 'table') }}`
//! - `{{ config(materialized='incremental', unique_key='id', ...) }}`
//! - `{% if is_incremental() %} ... {% endif %}` と `{{ this }}`
//! - `{{ env_var('NAME', 'default') }}`
//!
//! 同じテンプレートを2回描画する。1回目(parse)で依存関係と config を集め、
//! 2回目(render)で実際のテーブル名に置き換える。

use std::collections::{BTreeSet, HashMap};
use std::sync::{Arc, Mutex};

use anyhow::{Context, Result};
use minijinja::value::Kwargs;
use minijinja::{context, Environment, Error, ErrorKind, UndefinedBehavior};

#[derive(Debug, Default, Clone)]
pub struct Captured {
    pub refs: BTreeSet<String>,
    pub sources: BTreeSet<(String, String)>,
    pub config: serde_json::Map<String, serde_json::Value>,
}

/// 2回目の描画で使う名前解決。
#[derive(Debug, Default, Clone)]
pub struct Resolver {
    pub refs: HashMap<String, String>,
    pub sources: HashMap<(String, String), String>,
    pub is_incremental: bool,
    pub this: String,
}

enum Mode {
    Parse(Mutex<Captured>),
    Render(Resolver),
}

fn err(msg: impl Into<String>) -> Error {
    Error::new(ErrorKind::InvalidOperation, msg.into())
}

fn build_env(mode: Arc<Mode>) -> Environment<'static> {
    let mut env = Environment::new();
    env.set_undefined_behavior(UndefinedBehavior::Strict);
    env.set_keep_trailing_newline(true);

    let m = mode.clone();
    env.add_function("ref", move |name: String| -> Result<String, Error> {
        match &*m {
            Mode::Parse(c) => {
                c.lock().unwrap().refs.insert(name.clone());
                Ok(format!("__ref_{name}__"))
            }
            Mode::Render(r) => r
                .refs
                .get(&name)
                .cloned()
                .ok_or_else(|| err(format!("ref('{name}') を解決できません"))),
        }
    });

    let m = mode.clone();
    env.add_function(
        "source",
        move |src: String, table: String| -> Result<String, Error> {
            match &*m {
                Mode::Parse(c) => {
                    c.lock()
                        .unwrap()
                        .sources
                        .insert((src.clone(), table.clone()));
                    Ok(format!("__source_{src}_{table}__"))
                }
                Mode::Render(r) => r
                    .sources
                    .get(&(src.clone(), table.clone()))
                    .cloned()
                    .ok_or_else(|| err(format!("source('{src}', '{table}') が定義されていません"))),
            }
        },
    );

    let m = mode.clone();
    env.add_function("config", move |kwargs: Kwargs| -> Result<String, Error> {
        if let Mode::Parse(c) = &*m {
            let mut c = c.lock().unwrap();
            for key in kwargs.args() {
                let v: minijinja::Value = kwargs.get(key)?;
                let json = serde_json::to_value(&v).map_err(|e| err(e.to_string()))?;
                c.config.insert(key.to_string(), json);
            }
        } else {
            // 2回目は値を使わないが、未使用扱いのエラーを避けるために読む
            for key in kwargs.args() {
                let _: minijinja::Value = kwargs.get(key)?;
            }
        }
        Ok(String::new())
    });

    let m = mode.clone();
    env.add_function("is_incremental", move || -> bool {
        matches!(&*m, Mode::Render(r) if r.is_incremental)
    });

    env.add_function(
        "env_var",
        |name: String, default: Option<String>| -> Result<String, Error> {
            std::env::var(&name)
                .ok()
                .or(default)
                .ok_or_else(|| err(format!("環境変数 {name} が設定されていません")))
        },
    );

    env
}

fn render_with(name: &str, raw: &str, mode: Arc<Mode>, this: &str) -> Result<String> {
    let env = build_env(mode);
    let tmpl = env
        .template_from_named_str(name, raw)
        .with_context(|| format!("{name} のテンプレート構文エラー"))?;
    tmpl.render(context! { this => this })
        .map_err(|e| anyhow::anyhow!("{name} の描画に失敗: {e:#}"))
}

/// 1回目: 依存関係と config を集める(is_incremental() は false として扱う)。
pub fn parse(name: &str, raw: &str) -> Result<Captured> {
    let mode = Arc::new(Mode::Parse(Mutex::default()));
    render_with(name, raw, mode.clone(), &format!("__this_{name}__"))?;
    match Arc::try_unwrap(mode).ok().expect("環境は描画後に破棄済み") {
        Mode::Parse(c) => Ok(c.into_inner().unwrap()),
        Mode::Render(_) => unreachable!(),
    }
}

/// 2回目: 実際のテーブル名で SQL を作る。
pub fn render(name: &str, raw: &str, resolver: Resolver) -> Result<String> {
    let this = resolver.this.clone();
    let out = render_with(name, raw, Arc::new(Mode::Render(resolver)), &this)?;
    Ok(tidy(&out))
}

/// config() 呼び出しなどで残る先頭の空行と、行末の空白を除く。
fn tidy(sql: &str) -> String {
    let lines: Vec<&str> = sql.lines().map(str::trim_end).collect();
    let start = lines
        .iter()
        .position(|l| !l.is_empty())
        .unwrap_or(lines.len());
    let end = lines
        .iter()
        .rposition(|l| !l.is_empty())
        .map_or(start, |i| i + 1);
    let mut out = lines[start..end].join("\n");
    out.push('\n');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    const SQL: &str = r#"{{ config(materialized='incremental', unique_key='id', cluster_by=['a']) }}
select * from {{ ref('stg') }} join {{ source('shop', 'orders') }} using (id)
{% if is_incremental() %}where d > (select max(d) from {{ this }}){% endif %}
"#;

    #[test]
    fn parse_collects_refs_sources_and_config() {
        let c = parse("m", SQL).unwrap();
        assert_eq!(c.refs.iter().collect::<Vec<_>>(), vec!["stg"]);
        assert!(c.sources.contains(&("shop".into(), "orders".into())));
        assert_eq!(c.config["materialized"], "incremental");
        assert_eq!(c.config["cluster_by"], serde_json::json!(["a"]));
    }

    #[test]
    fn render_resolves_names() {
        let mut r = Resolver {
            this: "`p.d.m`".into(),
            ..Default::default()
        };
        r.refs.insert("stg".into(), "`p.d.stg`".into());
        r.sources
            .insert(("shop".into(), "orders".into()), "`p.raw.orders`".into());
        let full = render("m", SQL, r.clone()).unwrap();
        assert!(full.starts_with("select * from `p.d.stg` join `p.raw.orders`"));
        assert!(!full.contains("where d >"));

        r.is_incremental = true;
        let inc = render("m", SQL, r).unwrap();
        assert!(inc.contains("(select max(d) from `p.d.m`)"));
    }

    #[test]
    fn unknown_ref_or_variable_is_error() {
        assert!(render("m", "select {{ ref('x') }}", Resolver::default()).is_err());
        assert!(parse("m", "select {{ typo_var }}").is_err());
    }
}

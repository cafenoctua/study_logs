# dbt-impact 実装手順書

## 全体フェーズ

| Phase | 内容 | 目安時間 |
|-------|------|---------|
| 1 | プロジェクトセットアップ・manifest構造体定義 | 1〜2日 |
| 2 | グラフ探索（BFS）実装 | 2〜3日 |
| 3 | CLIインターフェース（clap）実装 | 1日 |
| 4 | 出力フォーマット（tree/list/json）実装 | 2日 |
| 5 | エラー処理・仕上げ | 1〜2日 |

---

## Phase 1: プロジェクトセットアップ・manifest構造体定義

### 1-1. Cargo.tomlにクレートを追加

```toml
[dependencies]
clap = { version = "4", features = ["derive"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "2"
```

### 1-2. manifest.rs の実装

**目標:** `manifest.json` を読み込んで `Manifest` 構造体にデシリアライズする。

実装するもの:
- `Manifest` 構造体（`nodes`, `sources`, `parent_map`, `child_map`）
- `Node` 構造体（`unique_id`, `name`, `resource_type`）
- `Manifest::load(path: &Path) -> Result<Manifest, ImpactError>`

**学習ポイント:** `serde` の `#[derive(Deserialize)]` と `#[serde(rename_all)]` によるフィールド名マッピング

---

## Phase 2: グラフ探索（BFS）実装

### 2-1. graph.rs の実装

**目標:** `parent_map` / `child_map` を使いBFSで依存関係を探索する。

実装するもの:
- `DependencyGraph` 構造体
- `DependencyGraph::from_manifest(manifest: &Manifest) -> Self`
- `fn upstream(root: &str, depth: Option<usize>) -> Vec<String>`
- `fn downstream(root: &str, depth: Option<usize>) -> Vec<String>`

**学習ポイント:** `VecDeque` を使ったBFS、`HashSet` による訪問済み管理

### 2-2. モデル名の正規化

manifest.jsonのキーは `"model.project.model_name"` 形式。  
ユーザーは `model_name` だけ入力するので、前方一致でキーを解決する関数が必要。

```rust
fn resolve_node_id(name: &str, nodes: &HashMap<String, Node>) -> Option<String>
```

---

## Phase 3: CLIインターフェース実装

### 3-1. main.rs の実装

**目標:** `clap` の derive マクロでコマンド定義を実装する。

```rust
#[derive(Parser)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Downstream { model: String, ... },
    Upstream   { model: String, ... },
}
```

**学習ポイント:** `clap` の derive API、`#[arg()]` によるオプション定義

---

## Phase 4: 出力フォーマット実装

### 4-1. output.rs の実装

**目標:** `tree` / `list` / `json` の3形式で結果を出力する。

`Formatter` トレイトを定義し、各形式を実装する:

```rust
trait Formatter {
    fn format(&self, root: &str, nodes: &[(String, usize)]) -> String;
    // usize は深さ（tree表示のインデント用）
}

struct TreeFormatter;
struct ListFormatter;
struct JsonFormatter;
```

**tree形式の深さ情報:** BFSの結果に `(node_id, depth)` のペアを持たせることでインデントを実現する。

**学習ポイント:** トレイトオブジェクト vs ジェネリクスの選択、`fmt::Display` の実装

---

## Phase 5: エラー処理・仕上げ

### 5-1. error.rs の実装（またはmanifest.rsに統合）

```rust
#[derive(Debug, thiserror::Error)]
enum ImpactError {
    #[error("manifest.json が見つかりません: {0}")]
    ManifestNotFound(PathBuf),

    #[error("manifest.json のパースに失敗しました: {0}")]
    ParseError(#[from] serde_json::Error),

    #[error("モデルが見つかりません: {0}")]
    ModelNotFound(String),
}
```

### 5-2. 動作確認

```bash
# ビルド
cargo build

# 実際のmanifest.jsonで動作確認
cargo run -- downstream stg_jaffle_shop_payment \
  --manifest ../dbt-dimensional-modeling/dbt_dimensional_modeling/target/manifest.json

# tree形式（デフォルト）
cargo run -- downstream stg_jaffle_shop_payment --format tree

# list形式
cargo run -- downstream stg_jaffle_shop_payment --format list

# depth制限
cargo run -- downstream stg_ga_sample --depth 2
```

---

## Phase 6: テストコード

### 全体方針

3種類のテストを全て実装する。

| テスト種別 | 配置 | 対象 | アクセスできる範囲 |
|-----------|------|------|------------------|
| ユニットテスト | 各 `src/*.rs` 末尾 | private含む関数・構造体 | `pub` / private 両方 |
| インテグレーションテスト | `tests/` ディレクトリ | pub な API の結合動作 | `pub` のみ |
| ドキュメントテスト | `///` コメント内 | pub な関数の使い方例 | `pub` のみ |

---

### 6-1. 事前準備：`lib.rs` の追加

インテグレーションテストとドキュメントテストは外部クレートとして `dbt-impact` を参照するため、`lib.rs` が必要です。

```
src/
  lib.rs       ← 新規追加
  main.rs
  graph.rs
  manifest.rs
  output.rs
  error.rs
tests/
  integration_test.rs  ← 新規追加
```

`lib.rs` は各モジュールを外部に公開するだけです：

```rust
// src/lib.rs
pub mod error;
pub mod graph;
pub mod manifest;
pub mod output;
```

`Cargo.toml` への追記は不要です（`lib.rs` が存在すれば自動認識されます）。

---

### 6-2. ユニットテスト（`graph.rs` / `output.rs`）

**配置:** 各ファイルの末尾に `#[cfg(test)] mod tests { ... }` を追加する。

**`graph.rs` のテスト対象:**

| テスト関数 | 確認内容 |
|-----------|---------|
| `test_resolve_found` | 存在するモデル名で `Ok` が返る |
| `test_resolve_not_found` | 存在しないモデル名で `Err` が返る |
| `test_downstream_root_depth` | rootノードの深さが0である |
| `test_downstream_depth_limit` | `depth=1` を指定すると深さ1までしか返らない |
| `test_upstream_root_depth` | upstream のrootの深さが0である |

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::{Manifest, Node, Source};
    use std::collections::HashMap;

    fn make_manifest() -> Manifest {
        let mut nodes = HashMap::new();
        nodes.insert("model.project.model_a".to_string(),
            Node::new("model.project.model_a", "model_a", "model"));
        nodes.insert("model.project.model_b".to_string(),
            Node::new("model.project.model_b", "model_b", "model"));

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
        Manifest { nodes, sources: HashMap::new(), parent_map, child_map }
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
        let result = graph.downstream("model_a", Some(0));
        assert_eq!(result.len(), 1);  // rootのみ
    }

    #[test]
    fn test_upstream_root_depth() {
        let graph = DependencyGraph::from_manifest(&make_manifest());
        let result = graph.upstream("model_b", None);
        assert_eq!(result[0].1, 0);
    }
}
```

**`output.rs` のテスト対象:**

| テスト関数 | 確認内容 |
|-----------|---------|
| `test_list_contains_all_nodes` | 全ノードが出力に含まれる |
| `test_tree_symbols` | `├──` と `└──` が含まれる |
| `test_tree_last_node_symbol` | 最後のノードが `└──` になる |
| `test_json_is_array` | `[` で始まり `]` で終わる |

---

### 6-3. インテグレーションテスト（`tests/`）

**配置:** `tests/integration_test.rs` を新規作成する。

**テスト対象:** `lib.rs` 経由で公開された `pub` な API の結合動作を確認する。

```rust
// tests/integration_test.rs
use dbt_impact::manifest::Manifest;
use dbt_impact::graph::DependencyGraph;
use std::path::Path;

#[test]
fn test_load_manifest_success() {
    let result = Manifest::load(Path::new("manifest.json"));
    assert!(result.is_ok());
}

#[test]
fn test_load_manifest_not_found() {
    let result = Manifest::load(Path::new("not_exist.json"));
    assert!(result.is_err());
}

#[test]
fn test_downstream_with_real_manifest() {
    let manifest = Manifest::load(Path::new("manifest.json")).unwrap();
    let graph = DependencyGraph::from_manifest(&manifest);
    let result = graph.downstream("stg_ga_sample", None);
    assert!(!result.is_empty());
}
```

---

### 6-4. ドキュメントテスト（`///` コメント）

**配置:** `pub` な関数の直上に `///` コメントとして書く。

**対象:** `Manifest::load` / `DependencyGraph::from_manifest` など外部から使われる関数。

```rust
// src/manifest.rs
impl Manifest {
    /// manifest.json を読み込んで Manifest 構造体を返す。
    ///
    /// # Examples
    ///
    /// ```no_run
    /// use dbt_impact::manifest::Manifest;
    /// use std::path::Path;
    ///
    /// let manifest = Manifest::load(Path::new("manifest.json")).unwrap();
    /// assert!(manifest.nodes.len() > 0);
    /// ```
    pub fn load(path: &Path) -> Result<Manifest, ImpactError> { ... }
}
```

`no_run` はファイルが存在しない環境でもコンパイルだけ確認するアノテーションです。

---

### テスト実行コマンド

```bash
cargo test                          # 全テスト実行
cargo test test_downstream          # 名前で絞り込み
cargo test -- --nocapture           # println! の出力を表示
cargo test --doc                    # ドキュメントテストのみ実行
cargo test --test integration_test  # インテグレーションテストのみ実行
```

---

### 実装順序

1. `graph.rs` にユニットテストを追加 → `cargo test` で動作確認
2. `output.rs` にユニットテストを追加 → フォーマッタの出力を確認
3. `src/lib.rs` を追加
4. `tests/integration_test.rs` を追加 → `cargo test --test integration_test`
5. `Manifest::load` にドキュメントテストを追加 → `cargo test --doc`

---

## 実装上の注意点

### モデル名の解決

ユーザー入力 `stg_jaffle_shop_payment` → manifest.jsonのキー `model.dbt_dimensional_modeling.stg_jaffle_shop_payment` への変換が必要。

複数マッチした場合はエラーにして候補を表示するのがUX的に親切。

### resource_typeの扱い

`child_map` / `parent_map` には `model` 以外に `source`, `seed`, `snapshot`, `analysis`, `test` も含まれる。  
デフォルトでは全種類を表示し、将来的に `--type model` でフィルタできるようにすると良い。

### tree表示のデータ構造

BFSで取得した `Vec<(node_id, depth)>` をそのままツリー表示に使う。  
実際のツリー構造（分岐の `├──` vs `└──`）を正確に描くには、兄弟ノードの有無を追跡する必要がある（Phase 4で検討）。

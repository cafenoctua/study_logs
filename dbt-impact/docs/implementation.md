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

# dbt-impact 設計書

## 概要

dbt の `manifest.json` を解析し、モデルの影響範囲（上流・下流依存）を即座に特定するCLIツール。

**解決する課題:** 「このモデルを変更したとき、何が壊れるか？」を手動でDAGを追うことなく即座に把握する。

---

## コマンド仕様

```bash
# 下流への影響（このモデルに依存しているものをすべて出す）
dbt-impact downstream <model_name> [OPTIONS]

# 上流への依存（このモデルが依存しているものをすべて出す）
dbt-impact upstream <model_name> [OPTIONS]
```

### オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--manifest <PATH>` | `./target/manifest.json` | manifest.jsonのパス |
| `--depth <N>` | 無制限 | 探索する深さの上限 |
| `--format <FORMAT>` | `tree` | 出力形式: `tree` / `list` / `json` |

### 出力例

**tree形式**
```
stg_jaffle_shop_payment
└── dim_customers
    └── analysis.check_dim_customers
```

**list形式**
```
dim_customers
analysis.check_dim_customers
```

**json形式**
```json
{
  "root": "stg_jaffle_shop_payment",
  "direction": "downstream",
  "nodes": ["dim_customers", "analysis.check_dim_customers"]
}
```

---

## アーキテクチャ

```
dbt-impact/
├── Cargo.toml
├── docs/
│   ├── design.md          # 本ファイル
│   └── implementation.md  # 実装手順書
└── src/
    ├── main.rs             # CLIエントリポイント（clap）
    ├── manifest.rs         # manifest.json構造体・デシリアライズ
    ├── graph.rs            # 依存グラフ・BFS探索
    └── output.rs           # 出力フォーマット（tree/list/json）
```

---

## データ構造

### manifest.json の該当箇所

```json
{
  "metadata": { "dbt_version": "1.9.3", ... },
  "nodes": {
    "model.project.model_name": {
      "unique_id": "model.project.model_name",
      "name": "model_name",
      "resource_type": "model",
      "depends_on": { "nodes": ["source.project.src.table"] }
    }
  },
  "sources": {
    "source.project.source_name.table": { ... }
  },
  "parent_map": {
    "model.project.model_name": ["source.project.src.table"]
  },
  "child_map": {
    "model.project.model_name": ["model.project.downstream_model"]
  }
}
```

### Rust構造体

```rust
// manifest.rs
struct Manifest {
    metadata: Metadata,
    nodes: HashMap<String, Node>,
    sources: HashMap<String, Source>,
    parent_map: HashMap<String, Vec<String>>,
    child_map: HashMap<String, Vec<String>>,
}

struct Node {
    unique_id: String,
    name: String,
    resource_type: String,
}

// graph.rs
struct DependencyGraph {
    // parent_map / child_map をそのまま保持
    // BFS探索で上流・下流を解決する
}
```

---

## 探索アルゴリズム

`child_map`（下流）または `parent_map`（上流）を使い、**BFS（幅優先探索）** で探索する。

```
入力: モデル名 "stg_jaffle_shop_payment", direction=downstream, depth=無制限

1. キュー = [("stg_jaffle_shop_payment", depth=0)]
2. visited = {}
3. child_map["model.project.stg_jaffle_shop_payment"] = ["model.project.dim_customers"]
4. → dim_customers をキューに追加 (depth=1)
5. child_map["model.project.dim_customers"] = ["analysis.project.check_dim_customers"]
6. → check_dim_customers をキューに追加 (depth=2)
7. キューが空になったら終了
```

depth指定がある場合は `depth >= max_depth` で探索を打ち切る。

---

## エラー処理

カスタムエラー型を `thiserror` クレートで定義する。

```rust
enum ImpactError {
    ManifestNotFound(PathBuf),
    ManifestParseError(serde_json::Error),
    ModelNotFound(String),
}
```

---

## 使用クレート

| クレート | 用途 |
|---------|------|
| `clap` | CLIパース（derive機能） |
| `serde` + `serde_json` | manifest.jsonのデシリアライズ |
| `thiserror` | カスタムエラー型の定義 |

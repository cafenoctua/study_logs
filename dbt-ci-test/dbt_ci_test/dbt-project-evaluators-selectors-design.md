# dbt_project_evaluator & selectors.yml 設計ドキュメント

本ドキュメントでは、dbt_project_evaluatorとselectors.ymlの設定について、設計意図・経緯・ベストプラクティスの観点からまとめます。

## 設計方針

### 基本原則

1. **公式推奨に従う**: dbt Labs公式ドキュメントの推奨事項を優先
2. **環境による動的制御**: 環境変数で挙動を切り替え可能に
3. **可読性と再利用性**: selectors.ymlで複雑なセレクターを管理
4. **CI/CDとローカル開発の分離**: 用途別にセレクターを定義

## dbt_project.yml 設計

### 1. テスト重大度の環境変数制御

```yaml
data_tests:
  dbt_project_evaluator:
    +severity: "{{ env_var('DBT_PROJECT_EVALUATOR_SEVERITY', 'warn') }}"
```

**設計意図:**

| 環境 | 設定値 | 理由 |
|------|--------|------|
| ローカル開発 | `warn` | 開発を妨げずに警告を表示 |
| CI環境 | `error` | PRマージ前に問題を検出・ブロック |

**経緯:**
- 当初は`+enabled`で有効/無効を切り替える案があった
- しかし、公式ドキュメントでは`severity`での制御を推奨
- 理由: 無効化すると問題が見えなくなるが、`warn`なら可視化される

**ベストプラクティス:**
- [dbt-project-evaluator CI Check](https://dbt-labs.github.io/dbt-project-evaluator/latest/ci-check/)に準拠
- `+enabled`は使用せず、`severity`で制御（問題の可視性を維持）

### 2. +enabled を使わない理由

```yaml
# 使用しない
# +enabled: "{{ env_var('DBT_PROJECT_EVALUATOR_ENABLED', 'true') ... }}"
```

**設計意図:**
- `+enabled: false`にすると、evaluatorモデルが全く生成されない
- 結果として、問題の存在自体が見えなくなる
- `severity: warn`なら警告は出るが、ビルドは失敗しない

**経緯:**
- README.mdでは`+enabled`の使用例があったが、再検討の結果削除
- selectors.ymlで除外する方がより明示的で制御しやすい

### 3. モデル設定のレイヤー分離

```yaml
models:
  dbt_ci_test:
    staging:
      +materialized: view
    intermediate:
      +materialized: ephemeral
    marts:
      +materialized: table
```

**設計意図:**
- evaluatorの命名規則チェックと整合性を取る
- レイヤーごとにmaterializationを明確化
- ディレクトリ構造 = 設定構造 = evaluatorの期待値

**ベストプラクティス:**
- dbt Labs推奨のレイヤー構造（staging → intermediate → marts）
- 各レイヤーに適切なmaterializationを設定

### 4. 命名規則の明示的定義

```yaml
vars:
  dbt_project_evaluator:
    # model_typesは文字列のリストで指定
    model_types: ['staging', 'intermediate', 'marts', 'other']

    # 各タイプの設定は別変数で定義
    staging_folder_name: 'staging'
    staging_prefixes: ['stg_']

    intermediate_folder_name: 'intermediate'
    intermediate_prefixes: ['int_']

    marts_folder_name: 'marts'
    marts_prefixes: ['fct_', 'dim_']

    other_folder_name: 'other'
    other_prefixes: ['']
```

**設計意図:**
- プロジェクトの命名規則を明文化
- evaluatorが正しくチェックできるように設定
- 新規参加者への規則の伝達

**注意点:**
- `model_types`は文字列のリストで指定（辞書のリストではない）
- 各タイプの設定は`<model_type>_folder_name`と`<model_type>_prefixes`で個別に定義
- 参考: [Structure Rules](https://dbt-labs.github.io/dbt-project-evaluator/0.8/rules/structure/)

**経緯:**
- デフォルト設定でも動作するが、明示的に定義することで:
  - ドキュメントとしての価値が生まれる
  - カスタマイズ箇所が明確になる
  - チーム内での認識統一ができる

## selectors.yml 設計

### 1. セレクター分類

| カテゴリ | セレクター | 用途 |
|----------|-----------|------|
| **CI/CD** | `ci_slim` | PR差分ビルド |
| | `ci_slim_with_tests` | PR差分 + 必須テスト |
| | `evaluator` | 構造解析のみ |
| **開発** | `dev_quick` | WIPモデルのみ |
| | `dev_full` | ローカルフルビルド |
| **本番** | `prod_full` | 本番フルビルド |
| | `prod_incremental` | 増分更新のみ |
| **レイヤー** | `layer_staging` | stagingのみ |
| | `layer_marts` | martsのみ |
| **テスト** | `unit_tests` | ユニットテストのみ |

### 2. ci_slim セレクター

```yaml
- name: ci_slim
  definition:
    method: state
    value: modified+
    exclude:
      - method: package
        value: dbt_project_evaluator
```

**設計意図:**
- Slim CIの実現（変更分のみビルド）
- evaluatorは別ステップで実行するため除外
- PRの実行時間を最小化

**経緯:**
- 当初はコマンドラインで`--exclude package:dbt_project_evaluator`を指定
- selectors.ymlに移行することで:
  - コマンドが簡潔になる
  - 設定がバージョン管理される
  - `dbt ls --selector ci_slim`でテスト可能

**ベストプラクティス:**
- [Best Practices for dbt Workflows](https://select.dev/posts/best-practices-for-dbt-workflows-1)に準拠
- state:modified+で差分+下流を選択

### 3. evaluator セレクター

```yaml
- name: evaluator
  definition:
    method: package
    value: dbt_project_evaluator
```

**設計意図:**
- evaluatorを独立したステップで実行
- CI結果を分離して表示可能に
- 失敗してもビルドステップには影響しない

**経緯:**
- dbt Labs公式推奨のCI構成:
  ```bash
  dbt build --select state:modified+ --exclude package:dbt_project_evaluator
  dbt build --select package:dbt_project_evaluator
  ```
- これをselectors.ymlで表現

### 4. dev_quick セレクター

```yaml
- name: dev_quick
  definition:
    method: tag
    value: wip
```

**設計意図:**
- 開発中のモデルにtag: wipを付与
- 素早くビルド・テストを繰り返せる
- 開発完了時にタグを外す運用

**ベストプラクティス:**
- [Understanding dbt Tags and Their Usage](https://hevodata.com/data-transformation/dbt-tags/)に準拠
- タグベースの開発ワークフロー

### 5. union による複合セレクター

```yaml
- name: ci_slim_with_tests
  definition:
    union:
      - method: state
        value: modified+
      - method: tag
        value: ci
    exclude:
      - method: package
        value: dbt_project_evaluator
```

**設計意図:**
- 変更分に加えて、常に実行すべきテストを含める
- tag: ciを付与したテストは必ず実行
- 回帰テストの確実な実行

**経緯:**
- PRによっては直接変更していないが影響を受けるテストがある
- そのようなテストにtag: ciを付与して漏れを防ぐ

## CI/CD ワークフロー設計

### GitHub Actions での使用例

```yaml
jobs:
  dbt-ci:
    steps:
      # Step 1: 差分ビルド
      - name: Build modified models
        run: dbt build --selector ci_slim --defer --state ./prod-manifest

      # Step 2: 構造解析
      - name: Run evaluator
        env:
          DBT_PROJECT_EVALUATOR_SEVERITY: error
        run: dbt build --selector evaluator
```

**設計意図:**
- ビルドと構造解析を分離
- 構造解析のseverityをCIでのみerrorに
- 各ステップの結果を独立して確認可能

## 設計決定のトレードオフ

### 1. severity vs enabled

| 観点 | severity制御 | enabled制御 |
|------|-------------|-------------|
| 問題の可視性 | 常に表示 | 無効時は非表示 |
| ビルド失敗の制御 | warn/errorで制御 | 完全に除外 |
| 推奨度 | 公式推奨 | 非推奨 |

**採用: severity制御**

### 2. コマンドライン vs selectors.yml

| 観点 | コマンドライン | selectors.yml |
|------|---------------|---------------|
| 柔軟性 | 高い | 事前定義必要 |
| 可読性 | 長くなる | 名前で参照 |
| バージョン管理 | CI設定に依存 | gitで管理 |
| テスト容易性 | 都度確認 | dbt lsで確認可能 |

**採用: ハイブリッド（基本はselectors.yml、動的制御は環境変数）**

### 3. 単一セレクター vs 複数セレクター

| 観点 | 単一（汎用） | 複数（用途別） |
|------|-------------|----------------|
| 管理コスト | 低い | 高い |
| 明確性 | 低い | 高い |
| 再利用性 | 高い | 用途限定 |

**採用: 複数セレクター（用途を明確化）**

## まとめ

### 設定ファイルの役割分担

| ファイル | 責務 |
|----------|------|
| `dbt_project.yml` | 動的制御（環境変数）、パッケージ設定 |
| `selectors.yml` | 静的なセレクター定義、用途別の選択条件 |
| CI workflow | 環境変数の設定、セレクターの呼び出し |

### ベストプラクティス準拠

- [dbt-project-evaluator CI Check](https://dbt-labs.github.io/dbt-project-evaluator/latest/ci-check/)
- [YAML Selectors | dbt Developer Hub](https://docs.getdbt.com/reference/node-selection/yaml-selectors)
- [Best Practices for dbt Workflows](https://select.dev/posts/best-practices-for-dbt-workflows-1)

### 今後の拡張ポイント

1. **チーム別セレクター**: `team_analytics`, `team_finance`など
2. **優先度別セレクター**: `priority_high`, `priority_low`など
3. **データソース別セレクター**: `source_salesforce`, `source_stripe`など

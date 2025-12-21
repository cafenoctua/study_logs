# selectors.yml vs 環境変数制御: 比較評価

dbt project evaluatorの実行制御について、selectors.ymlを使う方法と環境変数で制御する方法を比較評価します。

## 2つのアプローチ

### アプローチ1: 環境変数制御（現在のREADME）

```yaml
# dbt_project.yml
models:
  dbt_project_evaluator:
    +enabled: "{{ env_var('DBT_PROJECT_EVALUATOR_ENABLED', 'true') | lower == 'true' | as_bool }}"

data_tests:
  dbt_project_evaluator:
    +severity: "{{ env_var('DBT_PROJECT_EVALUATOR_SEVERITY', 'warn') }}"
```

### アプローチ2: selectors.yml

```yaml
# selectors.yml
selectors:
  - name: ci_build
    description: "CI用: 変更分のビルド（evaluator除外）"
    definition:
      method: state
      value: modified+
      exclude:
        - method: package
          value: dbt_project_evaluator

  - name: evaluator_only
    description: "dbt_project_evaluatorのみ実行"
    definition:
      method: package
      value: dbt_project_evaluator
```

## 比較表

| 観点 | 環境変数制御 | selectors.yml |
|------|-------------|---------------|
| **可読性** | 設定が分散（dbt_project.yml内） | 一箇所に集約、意図が明確 |
| **再利用性** | 環境変数名を覚える必要あり | `--selector name`で呼び出し可能 |
| **バージョン管理** | dbt_project.ymlに含まれる | 専用ファイルで差分追跡しやすい |
| **CI設定の複雑さ** | 環境変数の設定が必要 | コマンドがシンプル |
| **柔軟性** | 実行時に動的制御可能 | 事前定義が必要 |
| **dbt Cloud対応** | ネイティブサポート | ネイティブサポート |
| **デバッグ** | 環境変数の確認が必要 | `dbt ls --selector`でテスト可能 |

## 詳細評価

### メリット: selectors.yml

#### 1. 意図の明確化

```yaml
- name: ci_build
  description: "CI用: 変更分のビルド（evaluator除外）"
```

何のためのセレクターかがドキュメント化される。

#### 2. コマンドの簡潔化

```bash
# Before（環境変数）
DBT_PROJECT_EVALUATOR_ENABLED=false dbt build --select state:modified+

# After（selectors.yml）
dbt build --selector ci_build
```

#### 3. 複雑な選択条件の管理

```yaml
- name: full_ci
  definition:
    union:
      - method: state
        value: modified+
      - method: tag
        value: always_run
    exclude:
      - method: package
        value: dbt_project_evaluator
```

#### 4. テスト可能性

```bash
dbt ls --selector ci_build  # 対象モデルを事前確認
```

### デメリット: selectors.yml

1. **動的制御が難しい**
   - 環境変数のように実行時に挙動を変えられない
   - 例: 本番では実行、開発では無効化 → 環境変数の方が柔軟

2. **ファイル増加**
   - 小規模プロジェクトではオーバーヘッド

3. **学習コスト**
   - YAML構文の理解が必要

## ベストプラクティスの観点

### dbt Labs公式推奨

[dbt-project-evaluator CI Check](https://dbt-labs.github.io/dbt-project-evaluator/latest/ci-check/)では、**環境変数 + コマンドラインセレクター**の組み合わせを推奨:

```bash
dbt build --select state:modified+ --exclude package:dbt_project_evaluator
dbt build --select package:dbt_project_evaluator
```

### 推奨: ハイブリッドアプローチ

**両方を組み合わせる**のがベストプラクティス:

```yaml
# selectors.yml
selectors:
  - name: ci_modified
    description: "CI: 変更されたモデルのみ"
    definition:
      method: state
      value: modified+
      exclude:
        - method: package
          value: dbt_project_evaluator

  - name: evaluator
    description: "構造解析のみ"
    definition:
      method: package
      value: dbt_project_evaluator
```

```yaml
# dbt_project.yml（環境変数で厳格度を制御）
data_tests:
  dbt_project_evaluator:
    +severity: "{{ env_var('DBT_PROJECT_EVALUATOR_SEVERITY', 'warn') }}"
```

```yaml
# CI workflow
- name: Build modified models
  run: dbt build --selector ci_modified --defer --state ./prod-manifest

- name: Run structure analysis
  env:
    DBT_PROJECT_EVALUATOR_SEVERITY: error
  run: dbt build --selector evaluator
```

## 結論

| 用途 | 推奨方法 |
|------|----------|
| **実行対象の選択** | selectors.yml（可読性・再利用性） |
| **Severity制御** | 環境変数（動的制御が必要） |
| **有効/無効の切り替え** | 用途による（下記参照） |

### 有効/無効の切り替え

- **CI vs ローカル開発で分ける** → selectors.yml（明示的に除外）
- **同一コマンドで動的に切り替える** → 環境変数 `+enabled`

### 最終推奨

READMEのアプローチ（環境変数制御）は**正しい判断**です。理由:

1. dbt Labs公式が推奨する方法に沿っている
2. Severityの動的制御が可能
3. `+enabled`で完全無効化もできる

selectors.ymlは**補完的に使用**すると良い:

- 複雑な選択条件の管理
- チーム内でのコマンド標準化
- `dbt ls --selector`でのテスト

## 参考資料

- [YAML Selectors | dbt Developer Hub](https://docs.getdbt.com/reference/node-selection/yaml-selectors)
- [dbt-project-evaluator CI Check](https://dbt-labs.github.io/dbt-project-evaluator/latest/ci-check/)
- [dbt build selector: A Practical Guide](https://medium.com/@digital_hive/dbt-build-selector-a-practical-guide-f1873411dea9)
- [Best Practices for dbt Workflows](https://select.dev/posts/best-practices-for-dbt-workflows-1)

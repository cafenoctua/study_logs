# dbt project evaluatorを使ったモデル構造統制CI

## 概要

[dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator)は、dbt Labsが提供するパッケージで、dbtプロジェクトのベストプラクティス違反を自動検出します。

## チェックできるルール一覧

| カテゴリ | ルール | 説明 |
|---------|--------|------|
| **Modeling** | Direct join to source | ソースとモデルを同時参照していないか |
| | Downstream models dependent on source | mart/intがsourceを直接参照していないか |
| | Root models | 親を持たないモデルがないか |
| | Multiple sources joined | 複数ソースの直接結合がないか |
| **Testing** | Missing primary key tests | 主キーテストがあるか |
| | Test coverage | テストカバレッジ |
| **Documentation** | Undocumented models | 説明がないモデル |
| | Documentation coverage | ドキュメントカバレッジ |
| **Governance** | Public models without contract | publicモデルに契約があるか |
| | Undocumented public models | publicモデルのドキュメント |
| **Structure** | Model naming conventions | 命名規則 (stg_, int_, fct_, dim_) |
| | Model directories | ディレクトリ構造 |

## セットアップ

### 1. packages.yml

```yaml
packages:
  - package: dbt-labs/dbt_project_evaluator
    version: 0.8.1
```

### 2. dbt_project.yml

```yaml
models:
  # dbt_project_evaluator設定
  dbt_project_evaluator:
    +schema: dbt_project_evaluator

# マクロディスパッチ設定（BigQuery/Databricks/Spark/Redshift対応）
dispatch:
  - macro_namespace: dbt
    search_order: ['dbt_project_evaluator', 'dbt']

# 命名規則のカスタマイズ
vars:
  dbt_project_evaluator:
    model_types:
      - name: staging
        config:
          materialized: view
        folder: staging
        prefix: stg_
      - name: intermediate
        config:
          materialized: ephemeral
        folder: intermediate
        prefix: int_
      - name: marts
        config:
          materialized: table
        folder: marts
        prefix:
          - fct_
          - dim_
      - name: other
```

## CI/CD統合

### GitHub Actions設定

```yaml
name: dbt CI

env:
  DBT_PROFILES_DIR: ${{ github.workspace }}
  # テストのseverityをCIではerrorに
  DBT_PROJECT_EVALUATOR_SEVERITY: error

jobs:
  dbt-ci:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install dbt-bigquery

      - name: dbt deps
        run: dbt deps

      - name: dbt compile
        run: dbt compile --target ci

      # プロジェクトモデルのビルド（evaluator除外）
      - name: dbt build (project models)
        run: |
          dbt build \
            --exclude package:dbt_project_evaluator \
            --target ci

      # evaluatorの実行
      - name: Run dbt_project_evaluator
        run: |
          dbt build \
            --select package:dbt_project_evaluator \
            --target ci
```

### CIフロー

```
1. dbt deps          # パッケージインストール
2. dbt compile       # manifest生成
3. dbt build         # プロジェクトモデル（evaluator除外）
4. dbt build         # evaluatorパッケージ実行
5. PRコメント        # 結果をまとめて通知
```

## Severity設定

### デフォルト（warn）

ローカル開発時は警告のみ表示し、ビルドは継続します。

### CI/CD（error）

環境変数で制御:

```yaml
env:
  DBT_PROJECT_EVALUATOR_SEVERITY: error
```

または `dbt_project.yml` で設定:

```yaml
tests:
  dbt_project_evaluator:
    +severity: "{{ env_var('DBT_PROJECT_EVALUATOR_SEVERITY', 'warn') }}"
```

## 特定ルールの無効化

### 個別ルールを無効化

```yaml
vars:
  dbt_project_evaluator:
    # ドキュメントカバレッジチェックを無効化
    documentation_coverage_target: 0
    # テストカバレッジチェックを無効化
    test_coverage_target: 0
```

### 特定モデルを除外

```yaml
vars:
  dbt_project_evaluator:
    exclude_packages: ['external_package']
    models_excluded: ['legacy_model']
```

## PRコメント例

```markdown
# dbt CI Report

## dbt Project Evaluator Results

### Modeling Issues
| Model | Issue |
|-------|-------|
| fct_orders | Direct join to source detected |

### Documentation Issues
| Model | Coverage |
|-------|----------|
| Overall | 75% (target: 100%) |

### Naming Convention Violations
| Model | Expected | Actual |
|-------|----------|--------|
| orders | stg_orders | orders |
```

## 参考資料

- [dbt-project-evaluator GitHub](https://github.com/dbt-labs/dbt-project-evaluator)
- [Governance Rules](https://dbt-labs.github.io/dbt-project-evaluator/0.8/rules/governance/)
- [dbt blog: Introducing dbt_project_evaluator](https://docs.getdbt.com/blog/align-with-dbt-project-evaluator)
- [From Guidelines to Guardrails (Medium)](https://medium.com/data-science-collective/from-guidelines-to-guardrails-enforcing-dbt-best-practices-with-ci-cd-969e3a0747e3)

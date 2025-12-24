# dbtで堅牢なCIパイプラインを構築する - Slim CI、SDF Lint、dbt_project_evaluatorの実践

dbtプロジェクトでCIを構築する際、単純な`dbt build`だけでは不十分です。本記事では、実際に構築したdbt CIパイプラインの設計・実装について、Slim CI戦略、SDF Lintによるコード品質チェック、dbt_project_evaluatorによる構造解析を組み合わせた堅牢なCI構成を紹介します。

## 目次

1. [プロジェクト概要](#プロジェクト概要)
2. [CI設計の全体像](#ci設計の全体像)
3. [Slim CI戦略 - state:modified + defer](#slim-ci戦略---statemodified--defer)
4. [SDF Lintによるリンター・フォーマッター](#sdf-lintによるリンターフォーマッター)
5. [dbt_project_evaluatorによる構造解析](#dbt_project_evaluatorによる構造解析)
6. [selectors.ymlによるセレクター管理](#selectorsymlによるセレクター管理)
7. [GitHub Actionsワークフロー実装](#github-actionsワークフロー実装)
8. [つまずいたポイントと解決策](#つまずいたポイントと解決策)
9. [まとめ](#まとめ)

---

## プロジェクト概要

### 利用技術

| カテゴリ | 技術 |
|---------|------|
| dbt engine | dbt-core |
| DWH | BigQuery |
| CI/CD | GitHub Actions |
| リンター | SDF Lint |
| 構造解析 | dbt_project_evaluator |

### データパイプライン構成

BigQueryの公開データセット`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`を使用し、ディメンショナルモデリングに基づくパイプラインを構築しました。

```
models/
├── staging/
│   └── ga4/
│       └── stg_ga4__events.sql      # ソースデータの正規化
└── marts/
    ├── dim/
    │   ├── dim_users.sql            # ユーザー情報
    │   ├── dim_devices.sql          # 利用デバイス
    │   ├── dim_geo.sql              # アクセス地域
    │   └── dim_apps.sql             # アプリケーション情報
    └── fct/
        ├── fct_daily_engagement.sql # 日別利用時間
        ├── fct_daily_access.sql     # 日別アクセス数
        ├── fct_session_summary.sql  # セッションサマリー
        └── fct_user_ltv.sql         # ユーザーLTV
```

---

## CI設計の全体像

CIパイプラインは以下の3つの独立したジョブで構成されています。

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions Workflow                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐                                         │
│  │ update-prod-    │  manifest.jsonを生成                    │
│  │ manifest        │  (prod環境をparse)                      │
│  └────────┬────────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │   dbt-test      │  │   sdf-lint      │  ← 並列実行       │
│  │ (Slim CI +      │  │ (Format + Lint) │                   │
│  │  defer)         │  │                 │                   │
│  └────────┬────────┘  └─────────────────┘                   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                         │
│  │ dbt-evaluator   │  dbt_project_evaluator実行             │
│  │                 │                                         │
│  └─────────────────┘                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 各ジョブの役割

| ジョブ | 役割 | 実行タイミング |
|--------|------|---------------|
| update-prod-manifest | 本番環境のmanifest.jsonを生成 | 最初に実行 |
| dbt-test | 変更モデルのビルド・テスト | manifest生成後 |
| sdf-lint | SQLのフォーマット・リント | 並列実行可 |
| dbt-evaluator | プロジェクト構造の解析 | dbt-test完了後 |

---

## Slim CI戦略 - state:modified + defer

### なぜSlim CIが必要か

dbtプロジェクトが大きくなると、すべてのモデルをビルドするのは時間がかかります。PRで変更した部分だけをビルドすることで、CI実行時間を大幅に短縮できます。

### state:modifiedの仕組み

```bash
dbt build --select state:modified+ --defer --state ./prod_state
```

- `state:modified+`: 変更されたモデルとその下流を選択
- `--defer`: 未変更の上流モデルは本番環境を参照
- `--state ./prod_state`: 比較対象のmanifest.jsonを指定

### manifest.jsonの管理

本番環境のmanifest.jsonを生成し、Artifactとして保存します。

```yaml
# manifest.jsonの生成
- name: dbt parse (prod)
  run: dbt parse --target prod

# prod_stateディレクトリにコピー
- name: Update prod_state/manifest.json
  run: |
    mkdir -p prod_state
    cp target/manifest.json prod_state/manifest.json

# Artifactとして保存（mainブランチのみ）
- name: Upload prod manifest artifact
  if: github.ref == 'refs/heads/main'
  uses: actions/upload-artifact@v4
  with:
    name: prod-manifest
    path: dbt-ci-test/dbt_ci_test/prod_state/manifest.json
```

### 注意点: databaseフィールドの設定

manifest.jsonを生成する際、**必ず本番環境（prod）ターゲットでparseする**必要があります。

誤った設定だと`database`フィールドが空になり、defer時に以下のエラーが発生します：

```
Database Error in model fct_session_summary
  Syntax error: Invalid empty identifier at [17:19]
```

profiles.ymlでprojectを明示的に設定することで解決：

```yaml
prod:
  type: bigquery
  method: oauth
  project: "sweepsump"  # 必ず設定
  dataset: dbt_ci_test_prod
  location: US
```

---

## SDF Lintによるリンター・フォーマッター

### SDF Lintとは

[SDF](https://www.sdf.com/)は高速なSQLリンター・フォーマッターです。dbt Labsのブログで「1000倍高速」と紹介されています。

### セットアップ

1. インストール:
```bash
curl -LSfs https://cdn.sdf.com/releases/download/install.sh | sh -s
```

2. `workspace.sdf.yml`を作成:
```yaml
workspace:
  edition: '1.3'
  name: dbt_ci_test
  includes:
    - path: models
    - path: macros
      type: macro
  defaults:
    dialect: bigquery
    preprocessor: jinja

---
sdf-args:
  lint: >
    -w capitalization-keywords=consistent
    -w capitalization-literals=consistent
    -w capitalization-types=consistent
    -w capitalization-functions=consistent
    -w references-quoting
    -w structure-else-null
    -w structure-unused-cte
    -w structure-distinct
```

### Jinjaマクロの対応

SDF Lintはdbtのマクロ（`ref`、`source`など）をそのままでは認識できません。ダミーマクロを作成して対応します：

```sql
-- macros/ref.jinja
{%- macro ref(model_name) -%}
{{ model_name }}
{%- endmacro -%}
```

### CIでの実行

```yaml
- name: Run SDF format
  run: sdf format --save

- name: Commit formatting changes
  run: |
    git add -A
    if git diff --staged --quiet; then
      echo "No formatting changes"
    else
      git commit -m "style: auto-format SQL files with SDF"
      git push
    fi

- name: Run SDF lint
  run: sdf lint
```

---

## dbt_project_evaluatorによる構造解析

### dbt_project_evaluatorとは

[dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator)は、dbt Labsが提供するパッケージで、dbtプロジェクトのベストプラクティス違反を自動検出します。

### チェック可能なルール

| カテゴリ | ルール例 |
|---------|---------|
| Modeling | ソースへの直接結合、ルートモデルの検出 |
| Testing | 主キーテストの有無、テストカバレッジ |
| Documentation | ドキュメント未記載モデル、カバレッジ |
| Structure | 命名規則（stg_, int_, fct_, dim_）、ディレクトリ構造 |
| Governance | publicモデルの契約有無 |

### セットアップ

`packages.yml`:
```yaml
packages:
  - package: dbt-labs/dbt_project_evaluator
    version: 0.8.1
```

`dbt_project.yml`:
```yaml
# Severity制御（ローカル: warn、CI: error）
data_tests:
  dbt_project_evaluator:
    +severity: "{{ env_var('DBT_PROJECT_EVALUATOR_SEVERITY', 'warn') }}"

# evaluator用のスキーマ設定
models:
  dbt_project_evaluator:
    +schema: dbt_project_evaluator

# BigQuery対応のマクロディスパッチ
dispatch:
  - macro_namespace: dbt
    search_order: ['dbt_project_evaluator', 'dbt']

# 命名規則のカスタマイズ
vars:
  dbt_project_evaluator:
    model_types: ['staging', 'intermediate', 'marts', 'other']
    staging_folder_name: 'staging'
    staging_prefixes: ['stg_']
    intermediate_folder_name: 'intermediate'
    intermediate_prefixes: ['int_']
    marts_folder_name: 'marts'
    marts_prefixes: ['fct_', 'dim_']
```

### CIでの実行

```yaml
- name: Run dbt_project_evaluator
  env:
    DBT_PROJECT_EVALUATOR_SEVERITY: error  # CIではエラーとして扱う
  run: dbt build --selector evaluator
```

---

## selectors.ymlによるセレクター管理

### なぜselectors.ymlを使うのか

複雑な選択条件をYAMLで管理することで：

- コマンドが簡潔になる（`dbt build --selector ci_slim`）
- 設定がバージョン管理される
- `dbt ls --selector <name>`で事前確認可能

### セレクター定義

```yaml
selectors:
  # CI用: 変更モデル + 下流（evaluator除外）
  - name: ci_slim
    description: |
      CI用: 変更されたモデルとその下流のみをビルド。
      --state オプションと組み合わせて使用。
    definition:
      intersection:
        - method: state
          value: modified
          children: true
        - exclude:
            - method: package
              value: dbt_project_evaluator

  # evaluatorのみ
  - name: evaluator
    description: |
      構造解析: dbt_project_evaluatorパッケージのみを実行。
    definition:
      method: package
      value: dbt_project_evaluator

  # 開発用: WIPタグ付きモデル
  - name: dev_wip
    definition:
      intersection:
        - method: tag
          value: wip
          children: true
        - exclude:
            - method: package
              value: dbt_project_evaluator
```

### 注意: state:modified+の構文

`value: modified+`は**エラーになります**。以下のように記述します：

```yaml
# NG
- method: state
  value: modified+

# OK
- method: state
  value: modified
  children: true
```

---

## GitHub Actionsワークフロー実装

### 環境変数設定

```yaml
env:
  DBT_PROFILES_DIR: ${{ github.workspace }}/dbt-ci-test/dbt_ci_test
  DBT_BQ_PROJECT: sweepsump
  DBT_BQ_DATASET: dbt_ci_${{ format('pr{0}', github.event.pull_request.number) }}
  DBT_BQ_LOCATION: US
```

### profiles.yml

```yaml
dbt_ci_test:
  target: dev
  outputs:
    ci:
      type: bigquery
      method: oauth
      project: "sweepsump"
      dataset: "{{ env_var('DBT_BQ_DATASET', 'dbt_ci') }}"
      location: US
      threads: 4
      priority: interactive

    prod:
      type: bigquery
      method: oauth
      project: "sweepsump"
      dataset: dbt_ci_test_prod
      location: US
      threads: 4
      priority: batch
```

### dbt buildステップ（defer付き）

```yaml
- name: dbt build (slim CI with state:modified)
  run: |
    dbt build \
      --selector ci_slim \
      --defer \
      --state ./prod_state \
      --target ci
```

### PRコメントへの結果投稿

```yaml
- name: Post build results
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const report = fs.readFileSync('build_report.md', 'utf8');

      const { data: comments } = await github.rest.issues.listComments({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.issue.number
      });

      const botComment = comments.find(c =>
        c.user.type === 'Bot' && c.body.includes('dbt Build Results')
      );

      const body = `${report}\n\n---\n*Generated by dbt CI*`;

      if (botComment) {
        await github.rest.issues.updateComment({
          owner: context.repo.owner,
          repo: context.repo.repo,
          comment_id: botComment.id,
          body: body
        });
      } else {
        await github.rest.issues.createComment({
          owner: context.repo.owner,
          repo: context.repo.repo,
          issue_number: context.issue.number,
          body: body
        });
      }
```

---

## つまずいたポイントと解決策

### 1. BigQueryの"Request couldn't be served"エラー

**原因**: BigQueryのロケーション設定の不一致

**解決**: profiles.ymlで`location: US`を明示的に設定

### 2. state:modifiedで"does not match any enabled nodes"

**原因**: 変更がない場合のエラーハンドリング不足

**解決**: エラーメッセージを検出して成功として扱う

```bash
if grep -q "does not match any enabled nodes" dbt_build_output.txt; then
  echo "No modified models found - skipping build"
  exit 0
fi
```

### 3. defer時の"Invalid empty identifier"エラー

**原因**: manifest.jsonの`database`フィールドが空

**解決**: `dbt parse --target prod`でprod環境用のmanifestを生成

### 4. selectors.ymlの`modified+`構文エラー

**原因**: YAML selectors で`modified+`は無効

**解決**: `value: modified` + `children: true`に変更

### 5. SDF LintでJinjaマクロがエラー

**原因**: SDF LintがdbtのJinjaマクロを認識できない

**解決**: ダミーマクロを作成（`macros/ref.jinja`など）

---

## まとめ

### 設定ファイルの役割分担

| ファイル | 責務 |
|----------|------|
| `dbt_project.yml` | 環境変数による動的制御、パッケージ設定 |
| `selectors.yml` | 静的なセレクター定義、用途別の選択条件 |
| `profiles.yml` | 環境別の接続設定 |
| `dbt-ci.yml` | CIワークフロー、環境変数の設定 |

### ベストプラクティス

1. **Slim CI**: `state:modified` + `--defer`で差分のみビルド
2. **セレクター**: `selectors.yml`で複雑な条件を管理
3. **Severity制御**: 環境変数で`warn`/`error`を切り替え
4. **並列実行**: 独立したジョブは並列で実行
5. **PRコメント**: 結果を自動でPRにコメント

### 参考資料

- [dbt Docs: YAML Selectors](https://docs.getdbt.com/reference/node-selection/yaml-selectors)
- [dbt Docs: Defer to Production](https://docs.getdbt.com/reference/commands/build#defer)
- [dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator)
- [SDF: 1000x Faster SQL Linting](https://www.getdbt.com/blog/1000x-faster-sql-linting)
- [dbt Labs: CI Check](https://dbt-labs.github.io/dbt-project-evaluator/latest/ci-check/)

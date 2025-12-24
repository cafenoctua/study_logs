# dbt CI完全ガイド：差分ビルド・リンター・構成チェックを全部入りで実装してみた

## 概要

この記事では、dbtのCIについて以下必要だと考えられる処理全て詰め込んで見たものを検討した内容をまとめました。

- リンター・フォーマッター（SDF Lint）
- dbtの実行可能か（dbt build）
- データテスト
- ユニットテスト
- models.ymlの同期（dbt-osmosis）
- dbtプロジェクト構成違反検知（dbt_project_evaluator）

また、ここで重要になってくるのが都度の全実行だとCIとして非常に時間がかかるため**差分モデルのみに絞った処理（Slim CI）** を作ることを検討しています。

## 今回考えたCIの構成

### CIの実行概念図

```mermaid
flowchart TB
    subgraph trigger["トリガー"]
        PR["Pull Request to main"]
        WD["Workflow Dispatch（手動）"]
    end

    subgraph sdf["Job: sdf-lint（独立実行）"]
        SDF1["SDF format --save"]
        SDF2["変更があればコミット"]
        SDF3["SDF lint"]
        SDF4["結果をPRコメント"]
        SDF1 --> SDF2 --> SDF3 --> SDF4
    end

    subgraph dbt["Job: dbt-test"]
        subgraph step1["Step 1: prod manifest生成"]
            M1["dbt parse -t prod"]
            M2["prod_state/manifest.json に保存"]
            M1 --> M2
        end

        subgraph step2["Step 2: dbt build（defer戦略）"]
            B1["state:modified+ で差分検出"]
            B2["--defer で上流は本番参照"]
            B3["モデル実行 + データテスト + ユニットテスト"]
            B1 --> B2 --> B3
        end

        subgraph step3["Step 3: dbt-osmosis"]
            O1["変更モデルのディレクトリ検出"]
            O2["yaml refactor 実行"]
            O3["変更があればコミット"]
            O1 --> O2 --> O3
        end

        subgraph step4["Step 4: dbt_project_evaluator"]
            E1["最新コードをpull"]
            E2["dbt build --select package:dbt_project_evaluator"]
            E3["構成違反を検出"]
            E1 --> E2 --> E3
        end

        step1 --> step2 --> step3 --> step4
    end

    subgraph output["PRコメント出力"]
        C1["SDF Lint Results"]
        C2["dbt Build Results"]
        C3["dbt Project Evaluator Results"]
    end

    trigger --> sdf
    trigger --> dbt
    sdf --> C1
    dbt --> C2
    dbt --> C3
```

### CIごとの担当領域と出力内容

| ジョブ | 担当領域 | PRコメント | 自動コミット |
|--------|----------|------------|--------------|
| **sdf-lint** | SQL構文チェック・フォーマット | SDF Lint Results | フォーマット修正 |
| **dbt-test** | モデルビルド・テスト・構成チェック | Build Results / Evaluator Results | dbt-osmosis変更 |

## サンプルプロジェクトの構成

今回のCIを検証するため、GA4のサンプルデータを使ったディメンジョナルモデリングのプロジェクトを構築しました。

### ソースデータ

- `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`

### モデル構成

```
models/
├── staging/
│   └── ga4/
│       └── stg_ga4__events.sql      # ソースの正規化
└── marts/
    ├── dim/
    │   ├── dim_users.sql            # ユーザーディメンション
    │   ├── dim_devices.sql          # デバイスディメンション
    │   ├── dim_geo.sql              # 地域ディメンション
    │   └── dim_apps.sql             # アプリディメンション
    └── fct/
        ├── fct_daily_engagement.sql # 日次エンゲージメント
        ├── fct_daily_access.sql     # 日次アクセス
        ├── fct_user_ltv.sql         # ユーザーLTV
        └── fct_session_summary.sql  # セッションサマリー
```

### stagingモデルの例

```sql
-- models/staging/ga4/stg_ga4__events.sql
{{
    config(
        materialized='view'
    )
}}

with source as (
    select * from {{ source('ga4_ecommerce', 'events') }}
),

renamed as (
    select
        -- 日付・時間
        parse_date('%Y%m%d', event_date) as event_date,
        timestamp_micros(event_timestamp) as event_timestamp,

        -- イベント情報
        event_name,

        -- ユーザー情報
        user_id,
        user_pseudo_id,
        timestamp_micros(user_first_touch_timestamp) as user_first_touch_timestamp,

        -- デバイス情報
        device.category as device_category,
        device.operating_system as device_os,
        ...

    from source
)

select * from renamed
```

## CIの処理ごとに使った技術要素とその検討内容

### 1. SDF Lint（リンター・フォーマッター）

[SDF](https://www.sdf.com/)はRust製の高速SQLリンター・フォーマッターです。dbtプロジェクトにも対応しています。

#### workspace.sdf.yml の設定

```yaml
workspace:
  edition: '1.3'
  name: dbt_ci_test
  description: dbt ci test
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

#### CIでの実行フロー

1. `sdf format --save` でフォーマット適用
2. 変更があれば自動コミット
3. `sdf lint` でリント実行
4. 結果をPRコメントに投稿

```yaml
- name: Run SDF format
  run: |
    sdf format --save 2>&1 | tee sdf_format_output.txt

- name: Commit formatting changes
  run: |
    git add -A
    if git diff --staged --quiet; then
      echo "No formatting changes to commit"
    else
      git commit -m "style: auto-format SQL files with SDF"
      git push
    fi

- name: Run SDF lint
  run: |
    sdf lint 2>&1 | tee sdf_lint_output.txt
```

### 2. dbt build（Slim CI戦略）

#### defer戦略とは

変更があったモデルとその下流のみをビルドし、上流モデルは本番環境のテーブルを参照する戦略です。

```
[本番環境]          [CI環境]
┌─────────┐
│ staging │ ◄─────── defer で参照
└────┬────┘
     │
     ▼
┌─────────┐         ┌─────────┐
│  marts  │         │  marts  │ ← 変更があればビルド
└─────────┘         └─────────┘
```

#### 実装のポイント

```yaml
# Step 1: prod manifestの生成
- name: Generate prod manifest
  run: |
    dbt parse --target prod
    mkdir -p prod_state
    cp target/manifest.json prod_state/manifest.json

# Step 2: 差分ビルド
- name: dbt build (slim CI)
  run: |
    dbt build \
      --select state:modified+ \
      --defer \
      --state ./prod_state \
      --target ci \
      --exclude package:dbt_project_evaluator
```

**重要なオプション：**

| オプション | 説明 |
|------------|------|
| `--select state:modified+` | 変更されたモデルとその下流を選択 |
| `--defer` | 上流モデルは本番環境を参照 |
| `--state ./prod_state` | 比較対象のmanifest.jsonの場所 |
| `--exclude package:dbt_project_evaluator` | evaluatorは別途実行 |

#### selectors.yml での定義

```yaml
selectors:
  - name: ci_slim
    description: |
      CI用: 変更されたモデルとその下流のみをビルド。
    definition:
      intersection:
        - method: state
          value: modified
          children: true
        - exclude:
            - method: package
              value: dbt_project_evaluator
```

### 3. dbt-osmosis（models.yml同期）

[dbt-osmosis](https://github.com/z3z1ma/dbt-osmosis)は、dbtモデルのスキーマ定義（YAMLファイル）を自動生成・同期するツールです。

#### 差分ディレクトリのみ実行

```yaml
- name: Run dbt-osmosis yaml sync
  run: |
    MODIFIED_DIRS=$(git diff --name-only origin/main | \
      grep 'models/' | \
      xargs -I {} dirname {} | \
      sort -u)

    for dir in $MODIFIED_DIRS; do
      dbt-osmosis yaml refactor --fqn "$dir/"
    done
```

#### dbt_project.yml での配置設定

```yaml
models:
  dbt_ci_test:
    staging:
      +meta:
        dbt-osmosis: "_{parent}__models.yml"
    marts:
      dim:
        +meta:
          dbt-osmosis: "_dim__models.yml"
      fct:
        +meta:
          dbt-osmosis: "_fct__models.yml"
```

### 4. dbt_project_evaluator（構成違反チェック）

[dbt_project_evaluator](https://github.com/dbt-labs/dbt-project-evaluator)は、dbtプロジェクトのベストプラクティス違反を検出するパッケージです。

#### チェック項目

- **DAG構造**: ソースへの直接JOIN、stagingモデル間の依存など
- **命名規則**: プレフィックス（stg_, dim_, fct_）の一貫性
- **ドキュメント**: 未ドキュメントのモデル
- **テスト**: プライマリキーテストの欠落

#### dbt_project.yml での設定

```yaml
# テストの重大度を環境変数で制御
data_tests:
  dbt_project_evaluator:
    +severity: "{{ env_var('DBT_PROJECT_EVALUATOR_SEVERITY', 'warn') }}"

# 命名規則のカスタマイズ
vars:
  dbt_project_evaluator:
    model_types: ['staging', 'intermediate', 'marts', 'other']
    staging_prefixes: ['stg_']
    intermediate_prefixes: ['int_']
    marts_prefixes: ['fct_', 'dim_']
```

## GitHub Actions ワークフロー全体像

### トリガー設定

```yaml
on:
  pull_request:
    branches: [main]
    paths:
      - 'dbt-ci-test/dbt_ci_test/models/**'
      - 'dbt-ci-test/dbt_ci_test/macros/**'
      - 'dbt-ci-test/dbt_ci_test/tests/**'
      - '.github/workflows/dbt-ci.yml'

  workflow_dispatch:
    inputs:
      target:
        description: 'dbt target (ci/dev/prod)'
        type: choice
        options: [ci, dev, prod]
      run_dbt_test:
        description: 'Run dbt Build & Test job'
        type: boolean
        default: true
      run_sdf_lint:
        description: 'Run SDF Lint job'
        type: boolean
        default: true
      run_evaluator:
        description: 'Run dbt Project Evaluator job'
        type: boolean
        default: true
      run_osmosis:
        description: 'Run dbt-osmosis yaml sync'
        type: boolean
        default: true
      full_build:
        description: 'Run full build (ignore defer)'
        type: boolean
        default: false
```

### PRコメント出力例

#### SDF Lint Results

```markdown
## 🔍 SDF Lint Results

✅ All lint checks passed!

---
*Generated by dbt CI - SDF Lint*
```

#### dbt Build Results

```markdown
## 🔨 dbt Build Results

### Models
✅ **8** models succeeded

### Data Tests
✅ **12** tests passed

### Unit Tests
ℹ️ No unit tests executed

---
*Generated by dbt CI - Build & Test*
```

#### dbt Project Evaluator Results

```markdown
## 📊 dbt Project Evaluator Results

✅ All best practice checks passed!

**45** rules checked

---
*Generated by dbt CI - Project Evaluator*
```

## この検討中で浮かび上がった課題

### 1. SDF Lintの実用性

SDF Lintは高速で優れたツールですが、以下の課題があります：

- **Jinja関数の認識**: `ref()`, `source()` などのdbtマクロをエラーとして認識してしまう
- **回避策**: ダミーマクロを作成して対応が必要

```sql
-- macros/ref.jinja
{%- macro ref(model_name) -%}
{{ model_name }}
{%- endmacro -%}
```

SQLFluffの利用を継続する必要がありそうです。

### 2. CI実行時間の懸念

都度の `dbt build` / `dbt_project_evaluator` の実行は重いため、PRへの変更のたびに実行するのが良いか疑問があります。

**改善案：**

- `push`時は `dbt test --select test_type:unit` のみ実行
- `pull_request`時に全テスト実行
- `dbt_project_evaluator` はマージ前の最終チェックのみ

### 3. PR数が多い場合のデータセット競合

複数のPRが同時に実行される場合、CIで使用するデータセットが競合する可能性があります。

**現在の対策：**

```yaml
env:
  DBT_BQ_DATASET: dbt_ci_${{ format('pr{0}', github.event.pull_request.number) }}
```

PR番号ごとにデータセットを分けることで競合を回避しています。

## 今後の展望

1. **SQLFluff との併用検討**: SDF Lintの制約を考慮し、SQLFluffとの使い分けを検討
2. **CI実行の最適化**: pushトリガーでは軽量なユニットテストのみ実行
3. **キャッシュの活用**: `dbt deps` の結果をキャッシュしてCI時間を短縮
4. **コスト監視**: BigQueryのクエリコストを可視化してCI実行コストを管理

## まとめ

本記事では、dbt CIの「全部入り」構成を実装しました。主なポイントは：

- **Slim CI戦略**: `state:modified+` と `--defer` で差分ビルドを実現
- **自動化**: SDF formatとdbt-osmosisによる自動コミット
- **構成チェック**: dbt_project_evaluatorでベストプラクティス違反を検出
- **可視化**: 全ての結果をPRコメントとして出力

実際の運用では、CI実行時間とチェックの網羅性のバランスを考慮しながら、プロジェクトに合った構成を選択することが重要です。

## 参考文献

- [dbt Docs: Set up CI](https://docs.getdbt.com/guides/set-up-ci)
- [dbt-project-evaluator](https://dbt-labs.github.io/dbt-project-evaluator/)
- [dbt-osmosis](https://github.com/z3z1ma/dbt-osmosis)
- [SDF - 1000x faster SQL linting](https://www.getdbt.com/blog/1000x-faster-sql-linting)

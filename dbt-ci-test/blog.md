# はじめに

dbtプロジェクトのCI/CDを構築する機会があり、どのような構成が最適か検討しました。単純な`dbt build`だけでなく、Slim CI戦略、コード品質チェック、プロジェクト構造の検証を組み合わせた堅牢なCI構成を目指しました。

本記事では、実際に構築したdbt CIパイプラインの設計思想から実装詳細、そして直面した課題までを共有します。

### 利用技術

| カテゴリ | 技術 |
|---------|------|
| dbt engine | dbt-core |
| DWH | BigQuery |
| CI/CD | GitHub Actions |
| リンター | SDF Lint |
| 構造解析 | dbt_project_evaluator |

### 検証用データパイプライン

BigQueryの公開データセット`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`を使用し、以下のディメンショナルモデリング構成で検証しました。

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

# 今回考えた構成

CIパイプラインは以下の4つのジョブで構成しました。

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

| ジョブ | 役割 | 依存関係 |
|--------|------|---------|
| update-prod-manifest | 本番環境のmanifest.json生成 | なし（最初に実行） |
| dbt-test | 変更モデルのビルド・テスト | manifest生成後 |
| sdf-lint | SQLのフォーマット・リント | なし（並列実行可） |
| dbt-evaluator | プロジェクト構造の解析 | dbt-test完了後 |

### 設計ポイント

1. **独立性**: 各ジョブは独立して実行可能（workflow_dispatchで個別トリガー対応）
2. **並列化**: sdf-lintはdbt-testと並列実行し、CI時間を短縮
3. **結果通知**: 各ジョブの結果をPRコメントに自動投稿

---

# この構成に至るまでの思考

## 課題1: フルビルドは時間がかかりすぎる

dbtプロジェクトが成長すると、すべてのモデルをビルドするのは現実的ではありません。

**解決策: Slim CI（state:modified + defer）**

```bash
dbt build --select state:modified+ --defer --state ./prod_state
```

- 変更されたモデルとその下流のみビルド
- 未変更の上流モデルは本番環境を参照（defer）
- PR実行時間を大幅に短縮

## 課題2: コードスタイルの統一

チーム開発では、SQLのフォーマットがバラバラになりがちです。

**解決策: SDF Lint**

- 高速なSQLリンター・フォーマッター
- 自動フォーマット＋リントチェック
- dbt Labsブログで「1000倍高速」と紹介

## 課題3: プロジェクト構造のベストプラクティス遵守

命名規則やディレクトリ構造が守られているか、手動でチェックするのは大変です。

**解決策: dbt_project_evaluator**

- dbt Labsが提供する公式パッケージ
- 命名規則（stg_, int_, fct_, dim_）の検証
- ドキュメントカバレッジのチェック
- ソースへの直接結合の検出

## 課題4: 環境変数 vs selectors.yml

dbt_project_evaluatorの実行制御について、2つのアプローチを検討しました。

| 観点 | 環境変数制御 | selectors.yml |
|------|-------------|---------------|
| 可読性 | 設定が分散 | 一箇所に集約 |
| 動的制御 | 実行時に切替可能 | 事前定義が必要 |
| デバッグ | 環境変数確認必要 | `dbt ls --selector`でテスト可能 |

**採用: ハイブリッドアプローチ**
- 実行対象の選択 → selectors.yml（可読性・再利用性）
- Severity制御 → 環境変数（動的制御が必要）

---

# 構成の詳細

## 1. Slim CI - state:modified + defer

### manifest.jsonの管理

```yaml
# manifest.jsonの生成（prod環境）
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
    path: prod_state/manifest.json
```

### dbt buildステップ

```yaml
- name: dbt build (slim CI with state:modified)
  run: |
    dbt build \
      --selector ci_slim \
      --defer \
      --state ./prod_state \
      --target ci
```

## 2. SDF Lint

### workspace.sdf.yml

```yaml
workspace:
  edition: '1.3'
  name: dbt_ci_test
  includes:
    - path: models
    - path: macros
      type: macro  # Jinjaマクロ対応
  defaults:
    dialect: bigquery
    preprocessor: jinja

---
sdf-args:
  lint: >
    -w capitalization-keywords=consistent
    -w capitalization-literals=consistent
    -w structure-unused-cte
    -w structure-distinct
```

### Jinjaマクロ対応

SDF Lintはdbtのマクロを認識できないため、ダミーマクロを作成：

```sql
-- macros/ref.jinja
{%- macro ref(model_name) -%}
{{ model_name }}
{%- endmacro -%}
```

## 3. dbt_project_evaluator

### dbt_project.yml設定

```yaml
# Severity制御（ローカル: warn、CI: error）
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

## 4. selectors.yml

```yaml
selectors:
  # CI用: 変更モデル + 下流（evaluator除外）
  - name: ci_slim
    definition:
      intersection:
        - method: state
          value: modified
          children: true  # modified+の代わり
        - exclude:
            - method: package
              value: dbt_project_evaluator

  # evaluatorのみ
  - name: evaluator
    definition:
      method: package
      value: dbt_project_evaluator

  # 開発用: WIPタグ付きモデル
  - name: dev_wip
    definition:
      method: tag
      value: wip
      children: true
```

## 5. profiles.yml

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

    prod:
      type: bigquery
      method: oauth
      project: "sweepsump"
      dataset: dbt_ci_test_prod
      location: US
      threads: 4
```

---

# この構成の課題

## 1. manifest.jsonのdatabaseフィールド問題

**現象**: defer使用時に「Invalid empty identifier」エラー

**原因**: manifest.jsonの`database`フィールドが空

**解決策**: `dbt parse --target prod`でprod環境用のmanifestを生成。profiles.ymlでprojectを明示的に設定。

## 2. BigQueryロケーション不一致

**現象**: 「Request couldn't be served」エラー

**原因**: BigQueryのロケーション設定が不一致

**解決策**: profiles.ymlで`location: US`を明示的に設定

## 3. state:modified+のYAML構文

**現象**: selectors.ymlで`value: modified+`がエラー

**原因**: YAML selectorsでは`+`サフィックスは無効

**解決策**:
```yaml
# NG
value: modified+

# OK
value: modified
children: true
```

## 4. 変更がない場合のエラーハンドリング

**現象**: 変更モデルがないとき「does not match any enabled nodes」エラー

**解決策**: エラーメッセージを検出して成功として扱う
```bash
if grep -q "does not match any enabled nodes" output.txt; then
  echo "No modified models - skipping"
  exit 0
fi
```

## 5. PRごとのデータセット競合

**課題**: 複数PRが同時実行されると、同じCI用データセットで競合する可能性

**対策**: PR番号をデータセット名に含める
```yaml
DBT_BQ_DATASET: dbt_ci_pr${{ github.event.pull_request.number }}
```

---

# 参考文献と参考になったことまとめ

## 公式ドキュメント

| 資料 | 内容 |
|------|------|
| [dbt Docs: YAML Selectors](https://docs.getdbt.com/reference/node-selection/yaml-selectors) | セレクター構文の詳細 |
| [dbt Docs: Defer](https://docs.getdbt.com/reference/commands/build#defer) | defer機能の使い方 |
| [dbt-project-evaluator CI Check](https://dbt-labs.github.io/dbt-project-evaluator/latest/ci-check/) | CIでのevaluator活用法 |

## 参考になったブログ・記事

| 資料 | 学び |
|------|------|
| [SDF: 1000x Faster SQL Linting](https://www.getdbt.com/blog/1000x-faster-sql-linting) | SDF Lintの導入メリット |
| [Best Practices for dbt Workflows](https://select.dev/posts/best-practices-for-dbt-workflows-1) | Slim CI戦略のベストプラクティス |
| [From Guidelines to Guardrails](https://medium.com/data-science-collective/from-guidelines-to-guardrails-enforcing-dbt-best-practices-with-ci-cd-969e3a0747e3) | dbt_project_evaluatorでのガードレール構築 |

## 主な学び

1. **state:modifiedの`children: true`**: YAML selectorsでは`modified+`ではなく`children: true`を使う
2. **manifest.jsonの生成タイミング**: 必ずprodターゲットでparseしてdatabaseフィールドを正しく設定
3. **環境変数とselectorsの使い分け**: 静的な選択条件はselectors.yml、動的な制御は環境変数
4. **BigQueryのlocation**: 明示的に設定しないとリージョン不一致でエラーになる

---

# まとめ

## 設定ファイルの役割分担

| ファイル | 責務 |
|----------|------|
| `dbt_project.yml` | 環境変数による動的制御、パッケージ設定、命名規則 |
| `selectors.yml` | 静的なセレクター定義、用途別の選択条件 |
| `profiles.yml` | 環境別の接続設定（dev/ci/prod） |
| `dbt-ci.yml` | CIワークフロー、ジョブ構成、結果通知 |

## ベストプラクティス

1. **Slim CI**: `state:modified` + `--defer`で差分のみビルド
2. **セレクター管理**: `selectors.yml`で複雑な条件を一元管理
3. **Severity制御**: 環境変数でローカル`warn`/CI`error`を切り替え
4. **並列実行**: 独立したジョブ（sdf-lint）は並列で実行
5. **PRコメント**: 各ジョブの結果を自動でPRにフィードバック

## 今後の展望

- **チーム別セレクター**: `team_analytics`, `team_finance`など用途別セレクターの追加
- **キャッシュ活用**: dbt depsやpipインストールのキャッシュによる高速化
- **より詳細な結果レポート**: モデル実行時間、テストカバレッジの可視化

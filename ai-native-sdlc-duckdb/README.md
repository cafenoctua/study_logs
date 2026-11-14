# ai-native-sdlc-duckdb

「AI-Native SDLC サンプル構成」(GitHub + dbt + Python + Google Cloud)を、**クラウドリソースを使わず DuckDB でローカル完結**させた実装。

## クラウド版との対応

| クラウド版 | このサンプル |
|---|---|
| BigQuery `analytics_dev` / `analytics_ci_pr<N>` / `analytics` / `ops` | `warehouse/dev.duckdb` / `warehouse/ci.duckdb`(schema `analytics_ci_pr<N>`)/ `warehouse/prod.duckdb`(schema `analytics`, `ops`) |
| GCS の本番 `manifest.json` | `artifacts/prod-manifest/manifest.json` |
| Slim CI の defer 先(本番テーブル) | ci ターゲットが `prod.duckdb` を read_only で attach |
| `environment: production` の承認 | `scripts/deploy.sh` が承認者名の入力を要求 |
| サービスアカウント権限 | DuckDB の read_only 接続 + `.claude/settings.json` の deny + フック |
| `INFORMATION_SCHEMA.TABLE_STORAGE` | `count(*)` / `ops.deployments` の最終成功時刻 |
| claude-code-action の診断 + Issue | `artifacts/diagnose/*.md` にプロンプト出力(`RUN_CLAUDE=1` で `claude -p` 実行) |

## 構成

```
.claude/            settings.json(allow/deny・フック), hooks/, agents/verifier.md, skills/dbt-conventions/
docs/templates/     intent.md, spec.md, plan.md
docs/intents/       記録の例
models/             staging(view) / marts(table) + schema.yml
seeds/              raw_customers, raw_orders
monitoring/         metrics.yml, severity.py(σ判定), collect.py, detect.py, sql/ops_tables.sql, sql/kpi.sql
ci/                 upload_run_results.py, record.py
scripts/            ci.sh(ci.yml 相当), deploy.sh(deploy.yml 相当), init_ops.py, run_sql.py, seed_history.py
workflows/          Actions 版のサンプル(有効化するときはリポジトリ直下の .github/workflows/ へ)
tests/              pytest(フックと σ 判定)
CLAUDE.md, REVIEW.md
```

## 動かし方

```bash
cd ai-native-sdlc-duckdb
make setup && source .venv/bin/activate
make ops            # prod.duckdb に ops スキーマ
make test           # pytest 13件
make dev            # dbt build --target dev
make ci             # Slim CI(初回は prod manifest がないので全件 build)
make deploy         # 承認者名を入力 → prod build → manifest 保存 → ops 記録(main 以外は ALLOW_NON_MAIN=1)
make ci             # 2回目以降は state:modified+ / defer で変更分だけ
make monitor        # collect → detect(既定は shadow: 記録のみ)
make kpi            # 週次KPI
```

### 監視のデモ(段階3を出す)

```bash
python scripts/seed_history.py --anomaly     # 過去28日分 + 最新に行数3倍の異常
MONITOR_MODE=active python monitoring/detect.py
# stage= 3 row_count analytics.fct_orders zscore:+5.27
# diagnosis prompt -> artifacts/diagnose/<ts>.md
```

## 確認済み

- pytest 13件 PASS、`dbt build`(dev / ci / prod)PASS、sqlfluff lint クリーン
- モデル1つを変更したとき Slim CI が `fct_orders`, `dim_customers` だけを build すること
- 異常投入で段階3が記録され、active モードで診断プロンプトが出ること
- `workflows/` の Actions 定義は未実行(サンプル)

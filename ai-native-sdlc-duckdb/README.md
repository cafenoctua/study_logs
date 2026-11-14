# ai-native-sdlc-duckdb

「AI-Native SDLC サンプル構成」(GitHub + dbt + Python + Google Cloud)を、**クラウドリソースを使わず DuckDB でローカル完結**させた実装。**dbt v2**(`pip install dbt`)で動かす。

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

## dbt v2 について

- `dbt` パッケージ(v2)は単一バイナリ。DuckDB は ADBC ドライバ経由で、初回実行時に自動ダウンロードされる
- lint は v2 内蔵の `dbt lint`(SQLFluff 互換。`.sqlfluff` のルールコードをそのまま使う)。sqlfluff 本体は不要
- **Python 側の `duckdb` は 1.5 系に固定**。v2 の DuckDB ドライバ(1.5.x)と DB ファイル形式を合わせないと、`prod.duckdb` を開けなくなる(`version number 999` エラー)
- manifest は v12 形式のまま。`state:modified+` / `--defer` は v1 と同じコマンドで動く

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
workflows/          deploy / monitor / claude-review のサンプル(未有効化)。CI はリポジトリ直下 .github/workflows/ai-native-sdlc-duckdb-ci.yml で有効
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

- pytest 13件 PASS、`dbt build`(dev / ci / prod)PASS、`dbt lint` クリーン
- モデル1つを変更したとき Slim CI が `fct_orders`, `dim_customers` だけを build すること
- 異常投入で段階3が記録され、active モードで診断プロンプトが出ること
- CI は GitHub Actions で実行(`.github/workflows/ai-native-sdlc-duckdb-ci.yml`)。deploy / monitor / claude-review は未実行

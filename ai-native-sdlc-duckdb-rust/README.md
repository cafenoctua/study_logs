# ai-native-sdlc-duckdb-rust

PR #38 の `ai-native-sdlc-duckdb`(dbt v2 + DuckDB + Python)を、**dbt と Python を使わずすべて Rust** で書き直したもの。
クラウドリソースを使わず DuckDB でローカル完結する点、ディレクトリ構成と運用の流れ(記録 → 検証 → ガードレール → レビュー → 監視 → 計測)は元のままです。

## 置き換えの対応表

| PR #38(dbt v2 + Python) | このサンプル(Rust) | 備考 |
|---|---|---|
| dbt v2 単体バイナリ(`scripts/install_dbt.sh`) | `forge`(`crates/forge`) | ref / seed / view・table・incremental / データテスト / `state:modified+` / `--defer` |
| `dbt_project.yml` / `profiles.yml` | `forge_project.toml` / `profiles.toml` | schema.yml(テスト定義)は YAML のまま。dbt v2 の `arguments:` 形式も読める |
| `macros/generate_schema_name.sql` | `forge_project.toml` の `[seeds] schema = "raw"` | seed はスキーマ連結しない |
| `dbt lint`(v2 内蔵) | `forge lint` → sqruff(Rust 製) | 描画後の SQL を DuckDB 方言で lint |
| `dbt compile --target bq_compat --static-analysis strict` | `forge bq-compat` | sqlparser の BigQuery 方言で解析。**型の解析はしない**(下記) |
| `monitoring/{collect,detect,severity}.py` | `monitor collect` / `monitor detect` | 判定ロジックは `crates/monitor/src/severity.rs`(純粋関数) |
| `scripts/seed_history.py` | `monitor seed-history [--anomaly]` | |
| `ci/upload_run_results.py` / `ci/record.py` | `forge ops upload-results` / `record-deployment` / `record-ci-run` | |
| `scripts/init_ops.py` / `scripts/run_sql.py` | `forge ops init` / `forge query [--read-only]` | read_only は DuckDB が書き込みを拒否する |
| `.claude/hooks/*.py` | `guard protect-paths` / `guard lint-sql`(`crates/guard`) | |
| pytest(13件) | `cargo test`(フック・σ判定は同じケースを移植 + forge / monitor の結合テスト) | |
| Python 3.14 / `requirements.txt` / `.python-version` | なし | Rust の stable ツールチェーンだけ |
| `scripts/ci.sh` / `scripts/deploy.sh` / `Makefile` | 同名で残す(中身を forge / monitor 呼び出しに) | |

## 構成

```
crates/
  forge/      変換ツール(src/: config, project, template, graph, select, state, runner,
              materialize, warehouse(DuckDB), lint, bqcheck, ops)+ tests/build.rs
  monitor/    監視(src/severity.rs, src/lib.rs)+ tests/{severity,detect}.rs
  guard/      Claude Code のフック + tests/hooks.rs
.claude/      settings.json(allow/deny・フック), agents/verifier.md, skills/model-conventions/
docs/         templates/(intent, spec, plan), intents/(記録の例)
models/       staging(view) / marts(table) + schema.yml   ← PR #38 と同一
seeds/        raw_customers, raw_orders                   ← PR #38 と同一
monitoring/   metrics.yml, diagnose_prompt.md, sql/{ops_tables,kpi}.sql
scripts/      ci.sh(ci.yml 相当), deploy.sh(deploy.yml 相当)
workflows/    deploy / monitor / claude-review のサンプル(未有効化)
```

CI はリポジトリ直下 `.github/workflows/ai-native-sdlc-duckdb-rust-ci.yml`。

## 動かし方

```bash
cd ai-native-sdlc-duckdb-rust
make setup          # cargo build --release(初回は同梱 DuckDB の C++ ビルドで数分〜十数分)+ sqruff
export PATH=$PWD/target/release:$PATH   # make 以外から使うとき
make ops            # prod.duckdb に ops スキーマ
make test           # cargo test
make bq-compat      # BigQuery 互換チェック(接続なし)
make dev            # forge build --target dev
make ci             # Slim CI(初回は prod manifest がないので全件 build)
make deploy         # 承認者名を入力 → prod build → manifest 保存 → ops 記録(main 以外は ALLOW_NON_MAIN=1)
make ci             # 2回目以降は state:modified+ / defer で変更分だけ
make monitor        # collect → detect(既定は shadow: 記録のみ)
make kpi            # 週次KPI
```

### 監視のデモ(段階3を出す)

```bash
monitor seed-history --anomaly           # 過去28日分 + 最新に行数3倍の異常
MONITOR_MODE=active monitor detect
# stage= 3 row_count analytics.fct_orders zscore:+...
# diagnosis prompt -> artifacts/diagnose/<ts>.md
```

`RUN_CLAUDE=1` で `claude -p` に読み取り専用(`forge query --read-only` のみ)で渡すのは元と同じです。

## forge のコマンド

| コマンド | 内容 |
|---|---|
| `forge build / run / test / seed [-s …] [--state … --defer] [--full-refresh]` | build は seed・モデルを作ってすぐテスト。失敗したら下流はスキップ |
| `forge compile [-s …]` / `forge ls [-s …]` | 描画のみ(`forge_target/compiled/`)/ 選択の確認 |
| `forge lint [files…]` | 描画 → sqruff。引数なしで全モデル |
| `forge bq-compat` | BigQuery で通らない書き方を検出 |
| `forge query [--read-only] <sql or file.sql>` | `warehouse/prod.duckdb` に流す(`PROD_DB` で変更可) |
| `forge ops init / upload-results / record-deployment / record-ci-run` | ops スキーマへの記録 |

セレクタ: `model` / `model+` / `+model` / `state:modified` / `tag:x` / `path:models/marts`(空白・カンマは和集合)。

## dbt v2 との差(意図的に絞った範囲)

- **対応**:ref / source / seed / config / is_incremental / this / env_var、view・table・incremental(delete+insert)、unique / not_null / accepted_values / relationships、state:modified・defer、manifest / run_results
- **非対応**:マクロ・パッケージ、snapshot(SCD2)、ephemeral、カスタムテスト、`on_schema_change`(列の増減は `--full-refresh`)、ドキュメント生成、MetricFlow
- **並列実行しない**:DuckDB は1ファイルに書き込める接続が1つなので、依存順に直列で実行する(このサンプル規模では1秒未満)
- **BigQuery 互換チェックは構文レベル**:dbt v2 の静的解析は型まで見るが、`forge bq-compat` は BigQuery 方言での構文解析と、既知の DuckDB 専用の書き方(`count(*) filter (where …)`、`x::type`、`date_trunc('week', x)` の引数順、`varchar` / `double` 等の型名)の検出まで。型の不一致(例: 日付と文字列の比較)は検出できない
- **lint のルール**:dbt v2 内蔵 lint ではなく sqruff の既定ルール(`.sqruff` で dialect = duckdb)。行番号は描画後の SQL 基準なので、元ファイルと少しずれる
- **manifest の形式**:forge 独自(dbt の manifest v12 ではない)。PR #38 の本番 manifest は読めないので、切り替え後の初回 CI は全件 build になる
- **ops テーブル名**:`ops.dbt_run_results` → `ops.run_results`

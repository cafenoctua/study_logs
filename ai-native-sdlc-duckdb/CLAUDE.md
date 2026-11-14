# ai-native-sdlc-duckdb

dbt + DuckDB のローカル完結サンプル。クラウドは使わない。

## コマンド
- `make setup && source .venv/bin/activate` — 初回
- `make ops` — `warehouse/prod.duckdb` に ops スキーマ作成
- `make dev` — `dbt build --target dev`
- `make lint` / `dbt lint <file>` — SQL lint(v2 内蔵、SQLFluff 互換で `.sqlfluff` を読む)
- `make test` — pytest(フックと σ 判定)
- `make ci` — Slim CI 相当
- `make deploy` — **人間専用**。Claude は実行しない

## 命名
- `stg_<source>` / `fct_<event>` / `dim_<entity>`。詳細は `/dbt-conventions`

## 進め方
1. プランモードで計画し `docs/intents/<YYYY-MM-DD>-<slug>/plan.md` をコミット
2. 実装(SQL 編集のたびに自動 lint)
3. バグ修正は先に失敗するテストを書き、`LOCK_TESTS=1` で修正中のテスト改変を防ぐ
4. `verifier` サブエージェントが PASS したら PR。本文に intent/plan へのリンク

## 禁止
- `--target prod`、`warehouse/` の削除、`profiles.yml` / `scripts/deploy.sh` / フックの編集(フックで止まる)
- `git push`(人間が行う)

## よくあるミス
- `marts` で `stg_` を飛ばして seed を直接 ref する
- `left join` 後の集計で NULL を 0 にし忘れる(`coalesce`)
- prod.duckdb を開いたまま dbt を走らせてロック競合(DuckDB は単一ライター)

# ai-native-sdlc-duckdb-rust

DuckDB のローカル完結サンプル。クラウドは使わない。変換・監視・フックはすべて Rust(dbt と Python は使わない)。

## コマンド
- `make setup` — 初回(`cargo build --release` と sqruff のインストール)
- `make ops` — `warehouse/prod.duckdb` に ops スキーマ作成
- `make dev` — `forge build --target dev`
- `make lint` / `forge lint <file>` — 描画後の SQL を sqruff で lint
- `make bq-compat` — BigQuery で通らない書き方を接続なしで検出
- `make test` — `cargo test --workspace`(フック・σ判定・forge の結合テスト)
- `make ci` — Slim CI 相当
- `make deploy` — **人間専用**。Claude は実行しない
- 調査: `forge query --read-only "select ..."`(prod.duckdb を読み取り専用で開く)

## 構成
- `crates/forge` 変換ツール(seed/ref/view/table/incremental、データテスト、state:modified、defer、lint、bq-compat、ops 記録)
- `crates/monitor` 監視(collect / detect / seed-history、`severity.rs` が σ 判定)
- `crates/guard` Claude Code のフック

## 命名
- `stg_<source>` / `fct_<event>` / `dim_<entity>`。詳細は `/model-conventions`

## 進め方
1. プランモードで計画し `docs/intents/<YYYY-MM-DD>-<slug>/plan.md` をコミット
2. 実装(SQL 編集のたびに自動 lint)
3. バグ修正は先に失敗するテストを `crates/*/tests/` に書き、`LOCK_TESTS=1` で修正中のテスト改変を防ぐ
4. `verifier` サブエージェントが PASS したら PR。本文に intent/plan へのリンク

## 禁止
- `--target prod`、`warehouse/` の削除、`profiles.toml` / `scripts/deploy.sh` / `crates/guard/` の編集(フックで止まる)
- `forge ops ...`(記録はスクリプトだけが行う)
- `git push`(人間が行う)

## よくあるミス
- `marts` で `stg_` を飛ばして seed を直接 ref する
- `left join` 後の集計で NULL を 0 にし忘れる(`coalesce`)
- prod.duckdb を開いたまま forge を走らせてロック競合(DuckDB は単一ライター)
- `config()` のキーの綴り違い → forge は未知のキーをエラーにするので、エラー文を読んで直す

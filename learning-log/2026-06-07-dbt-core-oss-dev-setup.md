# 学習ログ: 2026-06-06〜2026-06-07 — dbt-core v2 OSS 開発環境セットアップ

## 学習したトピック
- dbt-core v2（Fusion/Rust 版）のビルド・動作確認環境の構築
- cargo nextest の使い方と cargo test との違い
- dbt-core v2 GitHub Issues の探索と最初のコントリビュート候補の選定

## 理解できたこと

### ツールチェーンの落とし穴
- `rust-toolchain.toml` が Rust 1.91 を指定しているが、`RUSTUP_TOOLCHAIN` 環境変数で別バージョンが固定されていると `error[E0658]` でビルドが失敗する
- 対処は `env -u RUSTUP_TOOLCHAIN cargo build -p dbt-sa-cli` で環境変数を外すだけでよい

### hello_world fixture で接続なし動作確認
- `crates/dbt-sa-cli/tests/data/hello_world/` の最小プロジェクトで `dbt parse` を実行できる
- `dbt parse` はデータベース接続不要。`target/manifest.json` が生成され v1 との差異比較もできる
- `compile`/`list` は DataFusion アダプタが未実装でパニックするため、接続なしで安定して動くのは `parse` と `--help` のみ

### direnv による dbt コマンドのセットアップ
- `.bin/dbt` を `target/debug/dbt-sa-cli` への symlink にし、`.envrc` で PATH に追加
- リポジトリ外に出ればグローバルの dbt（pip 版）に自動で戻る
- `cargo clean` で symlink が dangling になるが、再ビルドで直る

### cargo nextest vs cargo test
- nextest はテスト1件ごとに別プロセスを立ち上げる → プロセス分離によりテスト間汚染が起きない
- 大規模プロジェクトでは 2〜5 倍高速
- スタックサイズを `nextest.toml` で設定可能（`cargo test` は `RUST_MIN_STACK` 環境変数で対処）

### cargo nextest のインストール
- `cargo install cargo-nextest` だけではエラーになる
- `--locked` フラグが必須: `cargo install --locked cargo-nextest`

### コントリビュート候補 Issue の選び方
- `has-repro` / `repro/verified` ラベル付きが最優先（再現保証あり）
- `Conformance` ラベル付きは「v1 の動作に合わせるだけ」で仕様調査不要
- `needs-repro` のみは、再現確認コメントを書くだけでも貢献になる

## つまずいたこと・疑問点
- `cargo install cargo-nextest` が `locked-tripwire` クレートのコンパイルエラーで失敗した
  → `--locked` フラグを付けることで解消（nextest が意図的に制限している仕様）
- `cargo test` でスタックオーバーフロー（SIGABRT）が発生したことがある（2MBスタック不足）
  → `RUST_MIN_STACK=8388608` で解消（前セッション記録済み）

## 試したこと・調査内容
- `cargo nextest run -p dbt-sa-cli` の実行確認（nextest 未インストール → インストール手順確認）
- GitHub Issues の探索: `gh issue list --repo dbt-labs/dbt-core` で v2 関連バグを調査
- コントリビュート候補を `first-issue-candidates.md` としてメモリポジトリに保存

## 参照したドキュメント
- `crates/dbt-sa-cli/tests/data/hello_world/` — 動作確認用 fixture
- `CONTRIBUTING.md`（dbt-core リポジトリ直下）
- [changie 公式](https://changie.dev)
- [cargo-nextest インストール手順](https://nexte.st/docs/installation/from-source/)

---
*記録日時: 2026-06-07 15:42 / プロジェクト: dbt-core*

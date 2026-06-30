# 学習ログ: 2026-06-30 — dbt-core v2 (Rust) コントリビュート計画

## 学習したトピック
- dbt-core v2 (Rust/alpha) への OSS コントリビュートの進め方
- dbt 公式のコントリビュート期待値・マナー（CONTRIBUTING.md / Contributor Expectations）
- alpha 段階リポジトリ特有の運用（ブランチ二系統、copybara 同期）

## 理解できたこと
- **PR 先は常に `main`（v2/Rust）**。Python v1 は `1.latest` ブランチで別系統。
  issue によって対象ブランチが違うため、着手前に「Rust(main) 対象か」を確認する必要がある（実例: issue #10803）。
- **取り込み経路の特殊性**: Rust コードは社内モノレポと copybara で双方向同期される。
  main 宛マージ PR に `.rs` 変更が見えなくても、外部 PR が拒否されているわけではない。
- **必須マナー**（守らないと通らない）:
  - CLA サインが必須（initial PR 時）
  - すべての PR は issue に紐づける（"Every PR should be associated with an issue"）
  - 堅牢なテストを含める。文言修正でも既存テストで壊していない確認を明記
  - 小さく well-scoped に、後方互換を壊さない
  - レビューは2段階（product/usability → code review）
- ライセンス差: main = ELv2 / 1.latest = Apache-2.0
- 初手はロジックに触れない doc/help/文言修正が安全（alpha で内部構造が流動的なため）

## つまずいたこと・疑問点
- 当初「ブランチ二系統を確認して使い分ける」方針で計画を書いたが、
  実際は **v2/Rust のみ・PR 先は main に絞る** のが意図だった → 計画を修正。
  1.latest は対象外とし「取り違え防止の注意」だけ残す形に整理。
- CLA は「最初の壁」。今回 individual contributor の CLA フォームを記入・送付済み
  （contributor-license-agreements?version=2.0&name=Fusion）。

## 書いたコード・試したこと
- `~/codes/oss/dbt-core-develop-memos/contribution-plan.md` — 新規作成。
  6章構成（計画概要 / 事前知識 / マナー・期待値 / 実行チェックリスト / 検証 / 参考リンク）。
- `~/codes/oss/dbt-core-develop-memos/README.md` — ドキュメント一覧に新ファイルを追記。
- Claude のメモリに「コントリビュートのスコープ方針（v2/Rust・PR先=main）」を記録。

## 参照したドキュメント
- [dbt-core CONTRIBUTING.md](https://github.com/dbt-labs/dbt-core/blob/main/CONTRIBUTING.md)
- [Expectations for Open Source Contributors](https://docs.getdbt.com/community/resources/contributor-expectations)
- [Contributor License Agreements](https://docs.getdbt.com/community/resources/contributor-license-agreements?version=2.0&name=Fusion)
- [changie 公式](https://changie.dev)

---
*記録日時: 2026-06-30 23:11 / プロジェクト: dbt-core-develop-memos*

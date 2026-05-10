---
name: rust-docs
description: Rust について質問されたとき、関連する公式ドキュメントへのリンクと解説を提示する。/rust-docs が呼ばれたとき、または Rust の型・トレイト・関数・クレート・言語機能について質問されたときに必ず使う。ユーザーが Rust の概念を調べたい・公式ドキュメントを探したい・APIを確認したいと感じる場面では積極的に使うこと。
---

# Rust ドキュメント検索スキル

Rust の質問に対して、公式ドキュメントへの正確なリンクと解説を提示する。

## 使い方

ユーザーの質問・キーワードを受け取り、関連する公式ドキュメントを調べて提示する。

## ドキュメントの振り分け

質問の内容に応じて、以下のドキュメントから最適なものを選ぶ:

| 対象 | URL |
|------|-----|
| 標準ライブラリ API | https://doc.rust-lang.org/std/ |
| 言語仕様・文法 (Rust Reference) | https://doc.rust-lang.org/reference/ |
| 学習コンテンツ (The Book) | https://doc.rust-lang.org/book/ |
| The Book 日本語版 | https://doc.rust-jp.rs/book-ja/ |
| crate の API | https://docs.rs/ |
| unsafe 詳細 (Nomicon) | https://doc.rust-lang.org/nomicon/ |
| Cargo ガイド | https://doc.rust-lang.org/cargo/ |
| Clippy lints | https://rust-lang.github.io/rust-clippy/ |
| Rust by Example | https://doc.rust-lang.org/rust-by-example/ |

## 手順

1. 質問を分析し、どのカテゴリに該当するか判断する
2. WebSearch または WebFetch で関連ドキュメントページを確認する
3. 以下の形式で回答する

## 出力形式

```
## [概念名]

[100〜200字の概要説明（日本語）]

### 公式ドキュメント
- [The Rust Programming Language](URL) — 入門・概念理解向け
- [日本語版 The Book](URL) — あれば併記
- [Rust Reference](URL) — 言語仕様の詳細
- [std ドキュメント](URL) — API リファレンス

### 関連する主要な型・関数・トレイト
- [`型名`](URL) — 簡潔な説明

### 外部クレート（該当する場合）
- [docs.rs: crate名](URL) — 説明
```

## 注意事項

- 実在するページのリンクのみ提示する（存在確認できない URL は記載しない）
- 日本語版ドキュメントがある場合は必ず併記する
- Learning モード中のため、質問の背景にある概念も丁寧に補足する

# 学習ログ: 2026-06-06 — /learning-log スキルの作成と実動作検証

## 学習したトピック
- Claude Code のグローバルスキル（~/.claude/skills/）の作成と読み込み挙動
- スキル定義（フロントマター name/description、手順記述）の書き方
- メモリ（MEMORY.md + 個別ファイル）を使った作業の引き継ぎ

## 理解できたこと
- ~/.claude/skills/ 配下のスキルは起動時に読み込まれ、利用可能リスト/`/help` に表示される
- 保存先を「実行元プロジェクトを問わず常に ~/codes/study_logs/learning-log/ に固定」と明記することで集約できる
- 同日でも slug が異なれば別ファイルとして記録を分けられる
- 作業を中断する際は memory にスキル仕様（[[learning-log-skill]]）と検証手順（[[learning-log-verification-handoff]]）を残すと再起動後に再開できる

## つまずいたこと・疑問点
- ~/.claude/skills/ への新規スキルは動的反映が不確実 → 再起動で確実に読み込ませる必要があった
- learning-log/ ディレクトリは事前に存在せず、初回実行時に作成する必要がある

## 書いたコード・試したこと
- `~/.claude/skills/learning-log/SKILL.md` — 学習ログ記録スキル本体を新規作成
- memory に `learning-log-skill.md` / `learning-log-verification-handoff.md` を作成し引き継ぎ
- 実動作検証: slug 提案 → 内容提示 → 保存 → git commit のフローを通した

## 参照したドキュメント
- （特になし／Claude Code スキル仕様の自己検証）

---
*記録日時: 2026-06-06 11:14 / プロジェクト: codes*

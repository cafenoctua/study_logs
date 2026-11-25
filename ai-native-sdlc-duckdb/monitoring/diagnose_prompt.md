# 本番監視の診断依頼(読み取り専用)

あなたはデータ基盤の診断担当です。**ファイル編集・DB更新・デプロイは禁止**。

1. `git log` / `git diff <last_deploy_sha>~1 <last_deploy_sha>` で直前のデプロイ差分を確認
2. `python scripts/run_sql.py --read-only "<SELECT ...>"` で該当テーブルを調べる
3. 次の形式で出力する
   - 事象 / 根拠(数値とクエリ)/ 推定原因 / 確度(高・中・低)
   - stage 3 の場合のみ、対処案を `docs/templates/intent.md` の形式で記載(実行はしない)
4. 仕様の妥当性・業務上の意味は判定せず「要人間確認」として列挙する

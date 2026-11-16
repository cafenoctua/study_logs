---
name: dbt-conventions
description: このプロジェクトの dbt モデルを追加・変更するときの規約(層の責務、必須テスト、incremental、DuckDB 特有の注意)
---

# dbt 規約

## 層の責務
- `staging/stg_<source>`: 型変換・列名変更のみ。結合・集計しない。materialized=view
- `marts/fct_*`: 1行=1イベント。`dim_*`: 1行=1エンティティ。materialized=table
- モデル先頭に `-- 粒度: 1行 = ...` を書く

## 必須テスト
- 主キー: `unique` + `not_null`
- 外部キー: `relationships`
- 区分値: `accepted_values`

## incremental
- `unique_key` を必ず指定。`is_incremental()` の条件は遅延到着を考慮して数日ぶん重ねる
- DuckDB では `incremental_strategy='delete+insert'` を使う

## パーティション
- BigQuery 版の `partition_by` は DuckDB では不要。移植時に戻すことを intent に書く

## MetricFlow
- セマンティックモデルを足すときは粒度の列(`order_date` など)を変えない。変えるなら spec に影響範囲を書く

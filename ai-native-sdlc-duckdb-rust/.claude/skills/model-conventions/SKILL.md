---
name: model-conventions
description: このプロジェクトの SQL モデル(forge)を追加・変更するときの規約(層の責務、必須テスト、incremental、DuckDB と BigQuery の違い)
---

# モデル規約(forge)

## 層の責務
- `staging/stg_<source>`: 型変換・列名変更のみ。結合・集計しない。既定は view
- `marts/fct_*`: 1行=1イベント。`dim_*`: 1行=1エンティティ。既定は table
- モデル先頭に `-- 粒度: 1行 = ...` を書く
- seed(`seeds/*.csv`)は `raw` スキーマに入り、`{{ ref('raw_orders') }}` で参照する。marts から直接 ref しない

## テンプレートで使えるもの
- `{{ ref('x') }}` / `{{ source('src', 'table') }}` / `{{ this }}` / `{{ env_var('NAME', 'default') }}`
- `{{ config(materialized='view'|'table'|'incremental', unique_key=..., tags=[...]) }}`
- `{% if is_incremental() %} ... {% endif %}`
- マクロ・パッケージはない(必要なら forge に機能を足す PR を出す)

## 必須テスト(schema.yml)
- 主キー: `unique` + `not_null`
- 外部キー: `relationships`(`arguments: {to: ref('x'), field: y}`)
- 区分値: `accepted_values`(`arguments: {values: [...]}`)

## incremental
- `unique_key` を必ず指定(forge は delete+insert で反映する)。`is_incremental()` の条件は遅延到着を考慮して数日ぶん重ねる
- 列を増減したら `--full-refresh`

## BigQuery への移植を見据えて
- `forge bq-compat` が通る書き方にする。DuckDB だけで通る `count(*) filter (where ...)`、`x::type`、`date_trunc('week', x)`、`varchar` / `double` 型は使わない
- パーティションは DuckDB では不要。移植時に戻すことを intent に書く

## MetricFlow
- セマンティックモデルを足すときは粒度の列(`order_date` など)を変えない。変えるなら spec に影響範囲を書く

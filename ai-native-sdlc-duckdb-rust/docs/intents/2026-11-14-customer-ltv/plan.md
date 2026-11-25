# Plan: 顧客 LTV

## 手順
1. `fct_orders` に `is_revenue` を追加
2. `dim_customers` で completed のみ集計し left join、`coalesce(..., 0)`
3. `lifetime_value` に `not_null` テスト

## 検証
- `make ci` が PASS
- `python scripts/run_sql.py --read-only "select * from analytics.dim_customers"` で目視

## ロールバック
- 直前 SHA を checkout して `make deploy`

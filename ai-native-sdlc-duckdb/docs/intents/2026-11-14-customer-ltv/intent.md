# Intent: 顧客ごとの LTV を dim_customers に持たせる

- 起票: 2026-11-14 / sample

## 何を・なぜ
顧客分析で LTV を毎回集計しており、定義が人によってぶれている。`dim_customers.lifetime_value` に一本化する。

## 成功の判定
- [x] `dim_customers` の行数 = 顧客数(粒度不変)
- [x] cancelled / refunded は LTV に含めない
- [x] 注文のない顧客は LTV = 0

## やらないこと
- 通貨換算

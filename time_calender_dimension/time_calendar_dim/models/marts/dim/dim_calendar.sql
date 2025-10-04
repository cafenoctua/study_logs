{{
  config(
    materialized='table'
  )
}}

with date_spine as (
  select
    date_value
  from unnest(
    generate_date_array(date('2010-01-01'), date('2020-12-31'), interval 1 day)
  ) as date_value
),

calendar_base as (
  select
    date_value,

    -- サロゲートキー
    cast(format_date('%Y%m%d', date_value) as int64) as calendar_sk,

    -- 基本的な日付コンポーネント
    extract(year from date_value) as year_value,
    extract(month from date_value) as month_value,
    extract(day from date_value) as day_value,
    extract(quarter from date_value) as quarter_value,
    extract(week from date_value) as week_of_year,
    extract(dayofweek from date_value) as day_of_week,
    extract(dayofyear from date_value) as day_of_year,

    -- 月名と曜日名（英語）
    format_date('%B', date_value) as month_name_en,
    format_date('%b', date_value) as month_name_short_en,
    format_date('%A', date_value) as day_name_en,
    format_date('%a', date_value) as day_name_short_en,

    -- 月名と曜日名（日本語）
    case extract(month from date_value)
      when 1 then '1月'
      when 2 then '2月'
      when 3 then '3月'
      when 4 then '4月'
      when 5 then '5月'
      when 6 then '6月'
      when 7 then '7月'
      when 8 then '8月'
      when 9 then '9月'
      when 10 then '10月'
      when 11 then '11月'
      when 12 then '12月'
    end as month_name_jp,

    case extract(dayofweek from date_value)
      when 1 then '日曜日'
      when 2 then '月曜日'
      when 3 then '火曜日'
      when 4 then '水曜日'
      when 5 then '木曜日'
      when 6 then '金曜日'
      when 7 then '土曜日'
    end as day_name_jp,

    case extract(dayofweek from date_value)
      when 1 then '日'
      when 2 then '月'
      when 3 then '火'
      when 4 then '水'
      when 5 then '木'
      when 6 then '金'
      when 7 then '土'
    end as day_name_short_jp,

    -- 週末・平日フラグ
    case
      when extract(dayofweek from date_value) in (1, 7) then true
      else false
    end as is_weekend,

    case
      when extract(dayofweek from date_value) not in (1, 7) then true
      else false
    end as is_weekday,

    -- 月初・月末フラグ
    case
      when extract(day from date_value) = 1 then true
      else false
    end as is_first_day_of_month,

    case
      when date_value = last_day(date_value) then true
      else false
    end as is_last_day_of_month,

    -- 四半期の開始・終了
    case
      when date_value = date_trunc(date_value, quarter) then true
      else false
    end as is_first_day_of_quarter,

    case
      when date_value = date_sub(date_add(date_trunc(date_value, quarter), interval 1 quarter), interval 1 day) then true
      else false
    end as is_last_day_of_quarter,

    -- 年の開始・終了
    case
      when extract(dayofyear from date_value) = 1 then true
      else false
    end as is_first_day_of_year,

    case
      when extract(month from date_value) = 12 and extract(day from date_value) = 31 then true
      else false
    end as is_last_day_of_year,

    -- ISO週番号
    extract(isoweek from date_value) as iso_week_of_year,
    extract(isoyear from date_value) as iso_year,

    -- 会計年度（4月始まり）
    case
      when extract(month from date_value) >= 4 then extract(year from date_value)
      else extract(year from date_value) - 1
    end as fiscal_year_jp,

    case
      when extract(month from date_value) in (4, 5, 6) then 1
      when extract(month from date_value) in (7, 8, 9) then 2
      when extract(month from date_value) in (10, 11, 12) then 3
      when extract(month from date_value) in (1, 2, 3) then 4
    end as fiscal_quarter_jp,

    -- 日付の整数表現
    cast(format_date('%Y%m%d', date_value) as int64) as date_int,
    cast(format_date('%Y%m', date_value) as int64) as year_month_int,
    cast(format_date('%Y%Q', date_value) as int64) as year_quarter_int,

    -- 前日・翌日
    date_sub(date_value, interval 1 day) as previous_date,
    date_add(date_value, interval 1 day) as next_date,

    -- 同じ曜日の前週・翌週
    date_sub(date_value, interval 1 week) as same_day_previous_week,
    date_add(date_value, interval 1 week) as same_day_next_week,

    -- 前月・翌月の同じ日
    date_sub(date_value, interval 1 month) as same_day_previous_month,
    date_add(date_value, interval 1 month) as same_day_next_month,

    -- 前年・翌年の同じ日
    date_sub(date_value, interval 1 year) as same_day_previous_year,
    date_add(date_value, interval 1 year) as same_day_next_year,

    -- 月の日数
    extract(day from last_day(date_value)) as days_in_month,

    -- うるう年フラグ
    case
      when mod(extract(year from date_value), 400) = 0 then true
      when mod(extract(year from date_value), 100) = 0 then false
      when mod(extract(year from date_value), 4) = 0 then true
      else false
    end as is_leap_year

  from date_spine
)

select
  calendar_sk,
  date_value,
  year_value,
  month_value,
  day_value,
  quarter_value,
  week_of_year,
  day_of_week,
  day_of_year,
  month_name_en,
  month_name_short_en,
  month_name_jp,
  day_name_en,
  day_name_short_en,
  day_name_jp,
  day_name_short_jp,
  is_weekend,
  is_weekday,
  is_first_day_of_month,
  is_last_day_of_month,
  is_first_day_of_quarter,
  is_last_day_of_quarter,
  is_first_day_of_year,
  is_last_day_of_year,
  iso_week_of_year,
  iso_year,
  fiscal_year_jp,
  fiscal_quarter_jp,
  date_int,
  year_month_int,
  year_quarter_int,
  previous_date,
  next_date,
  same_day_previous_week,
  same_day_next_week,
  same_day_previous_month,
  same_day_next_month,
  same_day_previous_year,
  same_day_next_year,
  days_in_month,
  is_leap_year
from calendar_base
order by date_value
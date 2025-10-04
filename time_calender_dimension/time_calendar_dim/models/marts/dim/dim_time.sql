{{
  config(
    materialized='table'
  )
}}

with hours as (
  select hour_value
  from unnest(generate_array(0, 23)) as hour_value
),

minutes as (
  select minute_value
  from unnest(generate_array(0, 59)) as minute_value
),

time_spine as (
  select
    h.hour_value,
    m.minute_value
  from hours h
  cross join minutes m
),

time_dimension as (
  select
    -- サロゲートキー（HHMM形式の整数）
    hour_value * 100 + minute_value as time_sk,

    -- 基本的な時間コンポーネント
    hour_value,
    minute_value,
    hour_value * 60 + minute_value as minute_of_day,
    hour_value * 3600 + minute_value * 60 as second_of_day,

    -- 時間表記（文字列）
    format('%02d:%02d', hour_value, minute_value) as time_24h,
    format('%02d:%02d:00', hour_value, minute_value) as time_24h_full,

    -- 12時間表記
    case
      when hour_value = 0 then 12
      when hour_value <= 12 then hour_value
      else hour_value - 12
    end as hour_12h,

    format('%02d:%02d %s',
      case
        when hour_value = 0 then 12
        when hour_value <= 12 then hour_value
        else hour_value - 12
      end,
      minute_value,
      case
        when hour_value < 12 then 'AM'
        else 'PM'
      end
    ) as time_12h,

    -- AM/PM
    case
      when hour_value < 12 then 'AM'
      else 'PM'
    end as am_pm,

    case
      when hour_value < 12 then '午前'
      else '午後'
    end as am_pm_jp,

    -- 時間帯区分（詳細）
    case
      when hour_value between 0 and 4 then 'Early Morning'
      when hour_value between 5 and 8 then 'Morning'
      when hour_value between 9 and 11 then 'Late Morning'
      when hour_value between 12 and 13 then 'Noon'
      when hour_value between 14 and 16 then 'Afternoon'
      when hour_value between 17 and 18 then 'Evening'
      when hour_value between 19 and 21 then 'Night'
      when hour_value between 22 and 23 then 'Late Night'
    end as time_period_en,

    case
      when hour_value between 0 and 4 then '深夜'
      when hour_value between 5 and 8 then '早朝'
      when hour_value between 9 and 11 then '午前'
      when hour_value between 12 and 13 then '正午'
      when hour_value between 14 and 16 then '午後'
      when hour_value between 17 and 18 then '夕方'
      when hour_value between 19 and 21 then '夜'
      when hour_value between 22 and 23 then '深夜'
    end as time_period_jp,

    -- 時間帯区分（シンプル）
    case
      when hour_value between 6 and 11 then 'Morning'
      when hour_value between 12 and 17 then 'Afternoon'
      when hour_value between 18 and 23 then 'Evening'
      else 'Night'
    end as time_period_simple_en,

    case
      when hour_value between 6 and 11 then '朝'
      when hour_value between 12 and 17 then '昼'
      when hour_value between 18 and 23 then '夜'
      else '深夜'
    end as time_period_simple_jp,

    -- 営業時間区分
    case
      when hour_value between 9 and 17 then true
      else false
    end as is_business_hours,

    case
      when hour_value between 7 and 9 then true
      else false
    end as is_morning_rush,

    case
      when hour_value between 17 and 19 then true
      else false
    end as is_evening_rush,

    case
      when hour_value between 7 and 9 or hour_value between 17 and 19 then true
      else false
    end as is_rush_hour,

    -- 四半期時間（15分単位）
    cast(floor(minute_value / 15) as int64) + 1 as quarter_hour,

    case cast(floor(minute_value / 15) as int64)
      when 0 then '00-14'
      when 1 then '15-29'
      when 2 then '30-44'
      when 3 then '45-59'
    end as quarter_hour_label,

    -- 30分単位
    cast(floor(minute_value / 30) as int64) + 1 as half_hour,

    case cast(floor(minute_value / 30) as int64)
      when 0 then '00-29'
      when 1 then '30-59'
    end as half_hour_label,

    -- 食事時間フラグ
    case
      when hour_value between 7 and 9 then true
      else false
    end as is_breakfast_time,

    case
      when hour_value between 12 and 13 then true
      else false
    end as is_lunch_time,

    case
      when hour_value between 18 and 20 then true
      else false
    end as is_dinner_time,

    -- 時間の整数表現（結合用）
    cast(format('%02d%02d', hour_value, minute_value) as int64) as time_int,

    -- 次の時間
    case
      when hour_value = 23 and minute_value = 59 then '00:00'
      when minute_value = 59 then format('%02d:00', hour_value + 1)
      else format('%02d:%02d', hour_value, minute_value + 1)
    end as next_minute,

    -- 前の時間
    case
      when hour_value = 0 and minute_value = 0 then '23:59'
      when minute_value = 0 then format('%02d:59', hour_value - 1)
      else format('%02d:%02d', hour_value, minute_value - 1)
    end as previous_minute,

    -- 分類用の時間帯番号
    case
      when hour_value between 0 and 5 then 1
      when hour_value between 6 and 11 then 2
      when hour_value between 12 and 17 then 3
      when hour_value between 18 and 23 then 4
    end as time_period_id,

    -- 5分単位グループ
    cast(floor(minute_value / 5) as int64) + 1 as five_minute_group,
    format('%02d:%02d-%02d:%02d',
      hour_value,
      cast(floor(minute_value / 5) * 5 as int64),
      hour_value + case when cast(floor(minute_value / 5) * 5 + 4 as int64) > 59 then 1 else 0 end,
      case
        when cast(floor(minute_value / 5) * 5 + 4 as int64) > 59 then 0
        else cast(floor(minute_value / 5) * 5 + 4 as int64)
      end
    ) as five_minute_label,

    -- 10分単位グループ
    cast(floor(minute_value / 10) as int64) + 1 as ten_minute_group,
    format('%02d:%02d-%02d:%02d',
      hour_value,
      cast(floor(minute_value / 10) * 10 as int64),
      hour_value + case when cast(floor(minute_value / 10) * 10 + 9 as int64) > 59 then 1 else 0 end,
      case
        when cast(floor(minute_value / 10) * 10 + 9 as int64) > 59 then 0
        else cast(floor(minute_value / 10) * 10 + 9 as int64)
      end
    ) as ten_minute_label

  from time_spine
)

select
  time_sk,
  hour_value,
  minute_value,
  minute_of_day,
  second_of_day,
  time_24h,
  time_24h_full,
  hour_12h,
  time_12h,
  am_pm,
  am_pm_jp,
  time_period_en,
  time_period_jp,
  time_period_simple_en,
  time_period_simple_jp,
  is_business_hours,
  is_morning_rush,
  is_evening_rush,
  is_rush_hour,
  quarter_hour,
  quarter_hour_label,
  half_hour,
  half_hour_label,
  is_breakfast_time,
  is_lunch_time,
  is_dinner_time,
  time_int,
  next_minute,
  previous_minute,
  time_period_id,
  five_minute_group,
  five_minute_label,
  ten_minute_group,
  ten_minute_label
from time_dimension
order by time_sk
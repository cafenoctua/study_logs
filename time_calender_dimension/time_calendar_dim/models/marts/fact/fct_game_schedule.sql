{{
  config(
    materialized='table'
  )
}}

with stg_schedule as (
  select * from {{ ref('stg_schedule') }}
),

dim_calendar as (
  select * from {{ ref('dim_calendar') }}
),

dim_time as (
  select * from {{ ref('dim_time') }}
),

fact_base as (
  select
    -- サロゲートキー
    row_number() over (order by s.gameId, s.gameNumber) as game_schedule_sk,

    -- ゲーム識別子
    s.gameId,
    s.gameNumber,
    s.seasonId,
    s.year,

    -- 日付のサロゲートキー（dim_calendarと結合用）
    cast(format_date('%Y%m%d', date(s.startTime)) as int64) as game_date_sk,

    -- 時間のサロゲートキー（dim_timeと結合用）
    cast(extract(hour from s.startTime) * 100 + extract(minute from s.startTime) as int64) as game_time_sk,

    -- チーム情報
    s.homeTeamId,
    s.homeTeamName,
    s.awayTeamId,
    s.awayTeamName,

    -- 日時情報
    s.startTime,
    date(s.startTime) as game_date,
    extract(hour from s.startTime) as game_hour,
    extract(minute from s.startTime) as game_minute,

    -- ゲーム情報
    s.dayNight,
    s.type as game_type,
    s.duration,
    s.duration_minutes,

    -- ゲームステータス
    s.status,
    s.created,

    -- 観客数
    s.attendance

  from stg_schedule s
  where s.startTime is not null
)

select
  f.game_schedule_sk,
  f.game_date_sk,
  f.game_time_sk,
  f.gameId,
  f.gameNumber,
  f.seasonId,
  f.year,
  f.homeTeamId,
  f.homeTeamName,
  f.awayTeamId,
  f.awayTeamName,
  f.startTime,
  f.game_date,
  f.game_hour,
  f.game_minute,
  f.dayNight,
  f.game_type,
  f.duration,
  f.duration_minutes,
  f.status,
  f.created,
  f.attendance,

  -- dim_calendarと結合して日付属性を追加
  dc.year_value,
  dc.month_value,
  dc.day_value,
  dc.quarter_value,
  dc.week_of_year,
  dc.day_of_week,
  dc.day_of_year,
  dc.month_name_en,
  dc.month_name_short_en,
  dc.month_name_jp,
  dc.day_name_en,
  dc.day_name_short_en,
  dc.day_name_jp,
  dc.day_name_short_jp,
  dc.is_weekend,
  dc.is_weekday,
  dc.is_first_day_of_month,
  dc.is_last_day_of_month,
  dc.is_first_day_of_quarter,
  dc.is_last_day_of_quarter,
  dc.fiscal_year_jp,
  dc.fiscal_quarter_jp,
  dc.iso_week_of_year,
  dc.iso_year,

  -- dim_timeと結合して時間属性を追加
  dt.time_24h,
  dt.time_12h,
  dt.am_pm,
  dt.am_pm_jp,
  dt.time_period_en,
  dt.time_period_jp,
  dt.time_period_simple_en,
  dt.time_period_simple_jp,
  dt.is_business_hours,
  dt.is_morning_rush,
  dt.is_evening_rush,
  dt.is_rush_hour,
  dt.is_breakfast_time,
  dt.is_lunch_time,
  dt.is_dinner_time,
  dt.quarter_hour,
  dt.quarter_hour_label,
  dt.half_hour,
  dt.half_hour_label,
  dt.five_minute_group,
  dt.ten_minute_group

from fact_base f
left join dim_calendar dc
  on f.game_date_sk = dc.calendar_sk
left join dim_time dt
  on f.game_time_sk = dt.time_sk
order by f.startTime, f.gameId
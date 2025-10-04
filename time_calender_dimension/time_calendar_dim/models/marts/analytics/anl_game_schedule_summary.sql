{{
  config(
    materialized='table'
  )
}}

with game_schedule_facts as (
  select * from {{ ref('fct_game_schedule') }}
),

calendar_dimension as (
  select * from {{ ref('dim_calendar') }}
),

game_schedule_enriched as (
  select
    -- ゲーム基本情報
    f.game_schedule_sk,
    f.gameId,
    f.gameNumber,
    f.seasonId,
    f.year as season_year,

    -- チーム情報
    f.homeTeamId,
    f.homeTeamName,
    f.awayTeamId,
    f.awayTeamName,

    -- ゲーム詳細
    f.startTime,
    f.game_date,
    f.game_hour,
    f.dayNight,
    f.game_type,
    f.status,
    f.attendance,
    f.duration_minutes,

    -- カレンダー属性（日本語）
    c.date_value,
    c.year_value,
    c.month_value,
    c.month_name_jp,
    c.day_value,
    c.day_name_jp,
    c.day_name_short_jp,
    c.quarter_value,
    c.week_of_year,
    c.day_of_week,
    c.day_of_year,

    -- カレンダー属性（英語）
    c.month_name_en,
    c.month_name_short_en,
    c.day_name_en,
    c.day_name_short_en,

    -- 期間フラグ
    c.is_weekend,
    c.is_weekday,
    c.is_first_day_of_month,
    c.is_last_day_of_month,
    c.is_first_day_of_quarter,
    c.is_last_day_of_quarter,

    -- 会計年度（日本）
    c.fiscal_year_jp,
    c.fiscal_quarter_jp,

    -- ISO週
    c.iso_week_of_year,
    c.iso_year,

    -- うるう年
    c.is_leap_year,

    -- 派生指標
    case
      when f.game_hour between 6 and 11 then '朝（6-11時）'
      when f.game_hour between 12 and 17 then '昼（12-17時）'
      when f.game_hour between 18 and 23 then '夜（18-23時）'
      else '深夜（0-5時）'
    end as time_zone_jp,

    case
      when f.game_hour between 6 and 11 then 'Morning (6-11)'
      when f.game_hour between 12 and 17 then 'Afternoon (12-17)'
      when f.game_hour between 18 and 23 then 'Evening (18-23)'
      else 'Night (0-5)'
    end as time_zone_en,

    case
      when c.month_value in (3, 4, 5) then '春'
      when c.month_value in (6, 7, 8) then '夏'
      when c.month_value in (9, 10, 11) then '秋'
      when c.month_value in (12, 1, 2) then '冬'
    end as season_jp,

    case
      when c.month_value in (3, 4, 5) then 'Spring'
      when c.month_value in (6, 7, 8) then 'Summer'
      when c.month_value in (9, 10, 11) then 'Fall'
      when c.month_value in (12, 1, 2) then 'Winter'
    end as season_en

  from game_schedule_facts f
  inner join calendar_dimension c
    on f.game_date_sk = c.calendar_sk
),

-- 月次サマリー
monthly_summary as (
  select
    year_value,
    month_value,
    month_name_jp,
    month_name_en,
    count(distinct gameId) as total_games,
    count(distinct case when is_weekend then gameId end) as weekend_games,
    count(distinct case when is_weekday then gameId end) as weekday_games,
    sum(attendance) as total_attendance,
    avg(attendance) as avg_attendance,
    avg(duration_minutes) as avg_duration_minutes,
    count(distinct homeTeamId) as unique_home_teams,
    count(distinct awayTeamId) as unique_away_teams
  from game_schedule_enriched
  group by 1, 2, 3, 4
),

-- 曜日別サマリー
day_of_week_summary as (
  select
    day_of_week,
    day_name_jp,
    day_name_en,
    count(distinct gameId) as total_games,
    sum(attendance) as total_attendance,
    avg(attendance) as avg_attendance,
    avg(duration_minutes) as avg_duration_minutes
  from game_schedule_enriched
  group by 1, 2, 3
),

-- 時間帯別サマリー
time_zone_summary as (
  select
    time_zone_jp,
    time_zone_en,
    dayNight,
    count(distinct gameId) as total_games,
    sum(attendance) as total_attendance,
    avg(attendance) as avg_attendance
  from game_schedule_enriched
  group by 1, 2, 3
)

-- メインクエリ
select
  *
from game_schedule_enriched
order by date_value, startTime
{{
  config(
    materialized='table'
  )
}}

with fct_game as (
  select * from {{ ref('fct_game_schedule') }}
),

dim_cal as (
  select * from {{ ref('dim_calendar') }}
),

-- 基本メトリクス（日次粒度）
base_metrics as (
  select
    c.calendar_sk,
    c.date_value,
    c.year_value,
    c.month_value,
    c.day_value,
    c.quarter_value,
    c.week_of_year,
    c.iso_week_of_year,
    c.fiscal_year_jp,
    c.fiscal_quarter_jp,
    c.year_month_int,
    c.year_quarter_int,
    c.day_of_week,
    c.is_weekend,
    c.is_weekday,

    -- ゲームメトリクス
    count(f.gameId) as games_count,
    sum(f.attendance) as total_attendance,
    avg(f.attendance) as avg_attendance,
    max(f.attendance) as max_attendance,
    min(f.attendance) as min_attendance,
    sum(f.duration_minutes) as total_duration_minutes,
    avg(f.duration_minutes) as avg_duration_minutes,

    -- チーム統計
    count(distinct f.homeTeamId) as unique_home_teams,
    count(distinct f.awayTeamId) as unique_away_teams,

    -- デイ/ナイトゲーム
    sum(case when f.dayNight = 'D' then 1 else 0 end) as day_games,
    sum(case when f.dayNight = 'N' then 1 else 0 end) as night_games

  from dim_cal c
  left join fct_game f
    on c.calendar_sk = f.game_date_sk
  group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
)

-- マルチレベルロールアップ
select
  -- 日付階層
  date_value,
  year_value,
  month_value,
  day_value,
  quarter_value,
  week_of_year,
  iso_week_of_year,
  fiscal_year_jp,
  fiscal_quarter_jp,
  year_month_int,
  year_quarter_int,
  day_of_week,
  is_weekend,
  is_weekday,

  -- 日次メトリクス
  games_count as daily_games,
  total_attendance as daily_attendance,
  avg_attendance as daily_avg_attendance,
  max_attendance as daily_max_attendance,
  min_attendance as daily_min_attendance,
  total_duration_minutes as daily_total_duration,
  avg_duration_minutes as daily_avg_duration,
  unique_home_teams as daily_unique_home_teams,
  unique_away_teams as daily_unique_away_teams,
  day_games as daily_day_games,
  night_games as daily_night_games,

  -- 週次ロールアップ
  sum(games_count) over (
    partition by year_value, week_of_year
  ) as weekly_games,
  sum(total_attendance) over (
    partition by year_value, week_of_year
  ) as weekly_attendance,
  avg(avg_attendance) over (
    partition by year_value, week_of_year
  ) as weekly_avg_attendance,
  max(max_attendance) over (
    partition by year_value, week_of_year
  ) as weekly_max_attendance,

  -- 月次ロールアップ
  sum(games_count) over (
    partition by year_value, month_value
  ) as monthly_games,
  sum(total_attendance) over (
    partition by year_value, month_value
  ) as monthly_attendance,
  avg(avg_attendance) over (
    partition by year_value, month_value
  ) as monthly_avg_attendance,
  max(max_attendance) over (
    partition by year_value, month_value
  ) as monthly_max_attendance,
  count(case when games_count > 0 then 1 end) over (
    partition by year_value, month_value
  ) as monthly_days_with_games,

  -- 四半期ロールアップ
  sum(games_count) over (
    partition by year_value, quarter_value
  ) as quarterly_games,
  sum(total_attendance) over (
    partition by year_value, quarter_value
  ) as quarterly_attendance,
  avg(avg_attendance) over (
    partition by year_value, quarter_value
  ) as quarterly_avg_attendance,

  -- 年次ロールアップ
  sum(games_count) over (
    partition by year_value
  ) as yearly_games,
  sum(total_attendance) over (
    partition by year_value
  ) as yearly_attendance,
  avg(avg_attendance) over (
    partition by year_value
  ) as yearly_avg_attendance,
  max(max_attendance) over (
    partition by year_value
  ) as yearly_max_attendance,
  count(case when games_count > 0 then 1 end) over (
    partition by year_value
  ) as yearly_days_with_games,

  -- 会計年度ロールアップ（日本）
  sum(games_count) over (
    partition by fiscal_year_jp
  ) as fiscal_year_games,
  sum(total_attendance) over (
    partition by fiscal_year_jp
  ) as fiscal_year_attendance,

  sum(games_count) over (
    partition by fiscal_year_jp, fiscal_quarter_jp
  ) as fiscal_quarter_games,
  sum(total_attendance) over (
    partition by fiscal_year_jp, fiscal_quarter_jp
  ) as fiscal_quarter_attendance,

  -- 曜日別ロールアップ
  avg(games_count) over (
    partition by day_of_week
  ) as avg_games_by_day_of_week,
  avg(total_attendance) over (
    partition by day_of_week
  ) as avg_attendance_by_day_of_week,

  -- 週末/平日ロールアップ
  sum(games_count) over (
    partition by year_value, month_value, is_weekend
  ) as monthly_weekend_weekday_games,
  sum(total_attendance) over (
    partition by year_value, month_value, is_weekend
  ) as monthly_weekend_weekday_attendance,

  -- 累積メトリクス（年初からの累積）
  sum(games_count) over (
    partition by year_value
    order by date_value
    rows between unbounded preceding and current row
  ) as ytd_games,
  sum(total_attendance) over (
    partition by year_value
    order by date_value
    rows between unbounded preceding and current row
  ) as ytd_attendance,

  -- 累積メトリクス（月初からの累積）
  sum(games_count) over (
    partition by year_value, month_value
    order by date_value
    rows between unbounded preceding and current row
  ) as mtd_games,
  sum(total_attendance) over (
    partition by year_value, month_value
    order by date_value
    rows between unbounded preceding and current row
  ) as mtd_attendance,

  -- 移動平均（7日間）
  avg(games_count) over (
    order by date_value
    rows between 6 preceding and current row
  ) as ma7_games,
  avg(total_attendance) over (
    order by date_value
    rows between 6 preceding and current row
  ) as ma7_attendance,

  -- 移動平均（30日間）
  avg(games_count) over (
    order by date_value
    rows between 29 preceding and current row
  ) as ma30_games,
  avg(total_attendance) over (
    order by date_value
    rows between 29 preceding and current row
  ) as ma30_attendance,

  -- 前年同期比較
  lag(games_count, 365) over (
    order by date_value
  ) as prev_year_same_day_games,
  lag(total_attendance, 365) over (
    order by date_value
  ) as prev_year_same_day_attendance,

  -- 前月同日比較
  lag(games_count, 30) over (
    order by date_value
  ) as prev_month_same_day_games,
  lag(total_attendance, 30) over (
    order by date_value
  ) as prev_month_same_day_attendance,

  -- ランキング
  rank() over (
    partition by year_value
    order by total_attendance desc
  ) as yearly_attendance_rank,
  rank() over (
    partition by year_value, month_value
    order by total_attendance desc
  ) as monthly_attendance_rank,
  dense_rank() over (
    partition by year_value, quarter_value
    order by games_count desc
  ) as quarterly_games_rank

from base_metrics
order by date_value
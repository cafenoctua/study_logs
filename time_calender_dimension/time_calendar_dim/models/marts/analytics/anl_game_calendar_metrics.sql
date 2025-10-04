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

-- 日次ゲーム統計
daily_game_metrics as (
  select
    c.calendar_sk,
    c.date_value,
    c.year_value,
    c.month_value,
    c.day_value,
    c.quarter_value,
    c.week_of_year,
    c.day_of_week,
    c.month_name_jp,
    c.month_name_en,
    c.day_name_jp,
    c.day_name_en,
    c.is_weekend,
    c.is_weekday,
    c.fiscal_year_jp,
    c.fiscal_quarter_jp,

    -- ゲーム統計
    count(distinct f.gameId) as games_count,
    sum(f.attendance) as total_attendance,
    avg(f.attendance) as avg_attendance,
    max(f.attendance) as max_attendance,
    min(f.attendance) as min_attendance,
    avg(f.duration_minutes) as avg_game_duration,
    count(distinct f.homeTeamId) as unique_home_teams,
    count(distinct f.awayTeamId) as unique_away_teams,
    count(distinct case when f.dayNight = 'D' then f.gameId end) as day_games,
    count(distinct case when f.dayNight = 'N' then f.gameId end) as night_games

  from calendar_dimension c
  inner join game_schedule_facts f
    on c.calendar_sk = f.game_date_sk
  where c.date_value between date('2010-01-01') and date('2020-12-31')
  group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
),

-- 月次集計
monthly_aggregation as (
  select
    year_value,
    month_value,
    month_name_jp,
    month_name_en,
    fiscal_year_jp,
    fiscal_quarter_jp,

    -- 月次統計
    count(distinct case when games_count > 0 then date_value end) as days_with_games,
    count(distinct case when games_count = 0 then date_value end) as days_without_games,
    sum(games_count) as monthly_total_games,
    sum(total_attendance) as monthly_total_attendance,
    avg(avg_attendance) as monthly_avg_attendance,
    sum(day_games) as monthly_day_games,
    sum(night_games) as monthly_night_games,

    -- 週末vs平日
    sum(case when is_weekend then games_count else 0 end) as weekend_games,
    sum(case when is_weekday then games_count else 0 end) as weekday_games,
    sum(case when is_weekend then total_attendance else 0 end) as weekend_attendance,
    sum(case when is_weekday then total_attendance else 0 end) as weekday_attendance

  from daily_game_metrics
  group by 1, 2, 3, 4, 5, 6
),

-- 年次集計
yearly_aggregation as (
  select
    year_value,
    fiscal_year_jp,

    -- 年次統計
    count(distinct case when games_count > 0 then date_value end) as days_with_games,
    sum(games_count) as yearly_total_games,
    sum(total_attendance) as yearly_total_attendance,
    avg(avg_attendance) as yearly_avg_attendance,
    max(max_attendance) as yearly_max_attendance,

    -- 季節別ゲーム数
    sum(case when month_value in (3, 4, 5) then games_count else 0 end) as spring_games,
    sum(case when month_value in (6, 7, 8) then games_count else 0 end) as summer_games,
    sum(case when month_value in (9, 10, 11) then games_count else 0 end) as fall_games,
    sum(case when month_value in (12, 1, 2) then games_count else 0 end) as winter_games

  from daily_game_metrics
  group by 1, 2
),

-- 曜日別パターン分析
day_of_week_pattern as (
  select
    day_of_week,
    case day_of_week
      when 1 then '日曜日'
      when 2 then '月曜日'
      when 3 then '火曜日'
      when 4 then '水曜日'
      when 5 then '木曜日'
      when 6 then '金曜日'
      when 7 then '土曜日'
    end as day_name_jp,
    case day_of_week
      when 1 then 'Sunday'
      when 2 then 'Monday'
      when 3 then 'Tuesday'
      when 4 then 'Wednesday'
      when 5 then 'Thursday'
      when 6 then 'Friday'
      when 7 then 'Saturday'
    end as day_name_en,

    sum(games_count) as total_games,
    avg(games_count) as avg_games_per_day,
    sum(total_attendance) as total_attendance,
    avg(avg_attendance) as avg_attendance,
    sum(day_games) as day_games,
    sum(night_games) as night_games,

    -- 時間帯別の割合
    round(sum(day_games) * 100.0 / nullif(sum(games_count), 0), 2) as day_games_pct,
    round(sum(night_games) * 100.0 / nullif(sum(games_count), 0), 2) as night_games_pct

  from daily_game_metrics
  where games_count > 0
  group by 1
)

-- 最終出力
select
  d.*,

  -- ランキング情報を追加
  rank() over (order by d.total_attendance desc) as attendance_rank,
  rank() over (order by d.games_count desc) as games_count_rank,

  -- 前日比較
  lag(d.games_count, 1) over (order by d.date_value) as prev_day_games,
  lag(d.total_attendance, 1) over (order by d.date_value) as prev_day_attendance,

  -- 前年同日比較
  lag(d.games_count, 365) over (order by d.date_value) as prev_year_same_day_games,
  lag(d.total_attendance, 365) over (order by d.date_value) as prev_year_same_day_attendance

from daily_game_metrics d
order by d.date_value

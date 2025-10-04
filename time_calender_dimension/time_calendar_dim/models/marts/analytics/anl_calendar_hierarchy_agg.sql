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

-- GROUP BY ROLLUP相当の集計を実現
-- 各階層レベルでの集計を個別に計算してUNION ALL

-- レベル0: 全体集計
level_all as (
  select
    cast(null as int64) as year_value,
    cast(null as int64) as quarter_value,
    cast(null as int64) as month_value,
    cast(null as int64) as week_of_year,
    cast(null as int64) as day_value,
    cast(null as date) as date_value,
    'ALL' as aggregation_level,

    count(f.gameId) as total_games,
    sum(f.attendance) as total_attendance,
    avg(f.attendance) as avg_attendance,
    max(f.attendance) as max_attendance,
    min(f.attendance) as min_attendance,
    stddev(f.attendance) as stddev_attendance,
    count(distinct f.homeTeamId) as unique_home_teams,
    count(distinct f.awayTeamId) as unique_away_teams,
    count(distinct c.date_value) as days_with_data

  from dim_cal c
  left join fct_game f
    on c.calendar_sk = f.game_date_sk
  where c.date_value between date('2010-01-01') and date('2020-12-31')
),

-- レベル1: 年次集計
level_year as (
  select
    c.year_value,
    cast(null as int64) as quarter_value,
    cast(null as int64) as month_value,
    cast(null as int64) as week_of_year,
    cast(null as int64) as day_value,
    cast(null as date) as date_value,
    'YEAR' as aggregation_level,

    count(f.gameId) as total_games,
    sum(f.attendance) as total_attendance,
    avg(f.attendance) as avg_attendance,
    max(f.attendance) as max_attendance,
    min(f.attendance) as min_attendance,
    stddev(f.attendance) as stddev_attendance,
    count(distinct f.homeTeamId) as unique_home_teams,
    count(distinct f.awayTeamId) as unique_away_teams,
    count(distinct c.date_value) as days_with_data

  from dim_cal c
  left join fct_game f
    on c.calendar_sk = f.game_date_sk
  where c.date_value between date('2010-01-01') and date('2020-12-31')
  group by c.year_value
),

-- レベル2: 年-四半期集計
level_year_quarter as (
  select
    c.year_value,
    c.quarter_value,
    cast(null as int64) as month_value,
    cast(null as int64) as week_of_year,
    cast(null as int64) as day_value,
    cast(null as date) as date_value,
    'YEAR_QUARTER' as aggregation_level,

    count(f.gameId) as total_games,
    sum(f.attendance) as total_attendance,
    avg(f.attendance) as avg_attendance,
    max(f.attendance) as max_attendance,
    min(f.attendance) as min_attendance,
    stddev(f.attendance) as stddev_attendance,
    count(distinct f.homeTeamId) as unique_home_teams,
    count(distinct f.awayTeamId) as unique_away_teams,
    count(distinct c.date_value) as days_with_data

  from dim_cal c
  left join fct_game f
    on c.calendar_sk = f.game_date_sk
  where c.date_value between date('2010-01-01') and date('2020-12-31')
  group by c.year_value, c.quarter_value
),

-- レベル3: 年-月集計
level_year_month as (
  select
    c.year_value,
    cast(null as int64) as quarter_value,
    c.month_value,
    cast(null as int64) as week_of_year,
    cast(null as int64) as day_value,
    cast(null as date) as date_value,
    'YEAR_MONTH' as aggregation_level,

    count(f.gameId) as total_games,
    sum(f.attendance) as total_attendance,
    avg(f.attendance) as avg_attendance,
    max(f.attendance) as max_attendance,
    min(f.attendance) as min_attendance,
    stddev(f.attendance) as stddev_attendance,
    count(distinct f.homeTeamId) as unique_home_teams,
    count(distinct f.awayTeamId) as unique_away_teams,
    count(distinct c.date_value) as days_with_data

  from dim_cal c
  left join fct_game f
    on c.calendar_sk = f.game_date_sk
  where c.date_value between date('2010-01-01') and date('2020-12-31')
  group by c.year_value, c.month_value
),

-- レベル4: 年-週集計
level_year_week as (
  select
    c.year_value,
    cast(null as int64) as quarter_value,
    cast(null as int64) as month_value,
    c.week_of_year,
    cast(null as int64) as day_value,
    cast(null as date) as date_value,
    'YEAR_WEEK' as aggregation_level,

    count(f.gameId) as total_games,
    sum(f.attendance) as total_attendance,
    avg(f.attendance) as avg_attendance,
    max(f.attendance) as max_attendance,
    min(f.attendance) as min_attendance,
    stddev(f.attendance) as stddev_attendance,
    count(distinct f.homeTeamId) as unique_home_teams,
    count(distinct f.awayTeamId) as unique_away_teams,
    count(distinct c.date_value) as days_with_data

  from dim_cal c
  left join fct_game f
    on c.calendar_sk = f.game_date_sk
  where c.date_value between date('2010-01-01') and date('2020-12-31')
  group by c.year_value, c.week_of_year
),

-- レベル5: 年-月-日集計（最詳細）
level_year_month_day as (
  select
    c.year_value,
    cast(null as int64) as quarter_value,
    c.month_value,
    cast(null as int64) as week_of_year,
    c.day_value,
    c.date_value,
    'YEAR_MONTH_DAY' as aggregation_level,

    count(f.gameId) as total_games,
    sum(f.attendance) as total_attendance,
    avg(f.attendance) as avg_attendance,
    max(f.attendance) as max_attendance,
    min(f.attendance) as min_attendance,
    stddev(f.attendance) as stddev_attendance,
    count(distinct f.homeTeamId) as unique_home_teams,
    count(distinct f.awayTeamId) as unique_away_teams,
    count(distinct c.date_value) as days_with_data

  from dim_cal c
  left join fct_game f
    on c.calendar_sk = f.game_date_sk
  where c.date_value between date('2010-01-01') and date('2020-12-31')
  group by c.year_value, c.month_value, c.day_value, c.date_value
),

-- 全レベルを統合
all_levels as (
  select * from level_all
  union all
  select * from level_year
  union all
  select * from level_year_quarter
  union all
  select * from level_year_month
  union all
  select * from level_year_week
  union all
  select * from level_year_month_day
)

-- 最終出力
select
  aggregation_level,
  year_value,
  quarter_value,
  month_value,
  week_of_year,
  day_value,
  date_value,

  -- メトリクス
  total_games,
  total_attendance,
  avg_attendance,
  max_attendance,
  min_attendance,
  stddev_attendance,
  unique_home_teams,
  unique_away_teams,
  days_with_data,

  -- 派生メトリクス
  case
    when total_games > 0 then round(total_attendance / total_games, 0)
    else 0
  end as avg_attendance_per_game,

  case
    when days_with_data > 0 then round(total_games / days_with_data, 2)
    else 0
  end as avg_games_per_day,

  -- パフォーマンス指標
  case
    when avg_attendance > 35000 then '高'
    when avg_attendance > 25000 then '中'
    else '低'
  end as performance_category_jp,

  case
    when avg_attendance > 35000 then 'High'
    when avg_attendance > 25000 then 'Medium'
    else 'Low'
  end as performance_category_en

from all_levels
order by
  case aggregation_level
    when 'ALL' then 0
    when 'YEAR' then 1
    when 'YEAR_QUARTER' then 2
    when 'YEAR_MONTH' then 3
    when 'YEAR_WEEK' then 4
    when 'YEAR_MONTH_DAY' then 5
  end,
  year_value,
  quarter_value,
  month_value,
  week_of_year,
  date_value
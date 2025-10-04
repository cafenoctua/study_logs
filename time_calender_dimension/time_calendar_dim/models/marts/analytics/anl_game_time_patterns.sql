{{
  config(
    materialized='table'
  )
}}

with game_schedule_facts as (
  select * from {{ ref('fct_game_schedule') }}
),

dim_calendar as (
  select * from {{ ref('dim_calendar') }}
),

dim_time as (
  select * from {{ ref('dim_time') }}
),

-- ゲームスケジュールに時間と日付を完全結合
game_datetime_enriched as (
  select
    f.game_schedule_sk,
    f.game_date_sk,
    f.game_time_sk,
    f.gameId,
    f.gameNumber,
    f.seasonId,
    f.year as season_year,
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

    -- カレンダー属性
    c.calendar_sk,
    c.date_value,
    c.year_value,
    c.month_value,
    c.day_value,
    c.quarter_value,
    c.week_of_year,
    c.day_of_week,
    c.day_of_year,
    c.month_name_en,
    c.month_name_short_en,
    c.month_name_jp,
    c.day_name_en,
    c.day_name_short_en,
    c.day_name_jp,
    c.day_name_short_jp,
    c.is_weekend,
    c.is_weekday,
    c.is_first_day_of_month,
    c.is_last_day_of_month,
    c.fiscal_year_jp,
    c.fiscal_quarter_jp,
    c.iso_week_of_year,
    c.iso_year,

    -- 時間属性
    t.time_sk,
    t.hour_value,
    t.minute_value,
    t.time_24h,
    t.time_12h,
    t.am_pm,
    t.am_pm_jp,
    t.time_period_en,
    t.time_period_jp,
    t.time_period_simple_en,
    t.time_period_simple_jp,
    t.is_business_hours,
    t.is_morning_rush,
    t.is_evening_rush,
    t.is_rush_hour,
    t.is_breakfast_time,
    t.is_lunch_time,
    t.is_dinner_time,
    t.quarter_hour,
    t.quarter_hour_label,
    t.half_hour,
    t.half_hour_label,
    t.five_minute_group,
    t.ten_minute_group

  from game_schedule_facts f
  left join dim_calendar c
    on f.game_date_sk = c.calendar_sk
  left join dim_time t
    on f.game_time_sk = t.time_sk
  where f.startTime is not null
),

-- 時間帯別ゲーム分析
time_period_analysis as (
  select
    time_period_jp,
    time_period_en,
    count(distinct gameId) as total_games,
    sum(attendance) as total_attendance,
    avg(attendance) as avg_attendance,
    avg(duration_minutes) as avg_duration,

    -- 曜日別内訳
    count(distinct case when day_of_week = 1 then gameId end) as sunday_games,
    count(distinct case when day_of_week = 2 then gameId end) as monday_games,
    count(distinct case when day_of_week = 3 then gameId end) as tuesday_games,
    count(distinct case when day_of_week = 4 then gameId end) as wednesday_games,
    count(distinct case when day_of_week = 5 then gameId end) as thursday_games,
    count(distinct case when day_of_week = 6 then gameId end) as friday_games,
    count(distinct case when day_of_week = 7 then gameId end) as saturday_games,

    -- 週末vs平日
    count(distinct case when is_weekend then gameId end) as weekend_games,
    count(distinct case when is_weekday then gameId end) as weekday_games,

    -- 季節別
    count(distinct case when month_value in (3,4,5) then gameId end) as spring_games,
    count(distinct case when month_value in (6,7,8) then gameId end) as summer_games,
    count(distinct case when month_value in (9,10,11) then gameId end) as fall_games,
    count(distinct case when month_value in (12,1,2) then gameId end) as winter_games

  from game_datetime_enriched
  group by 1, 2
),

-- 時間別詳細分析
hourly_analysis as (
  select
    hour_value,
    format('%02d:00', hour_value) as hour_label,
    am_pm_jp,
    am_pm,

    count(distinct gameId) as total_games,
    sum(attendance) as total_attendance,
    avg(attendance) as avg_attendance,
    stddev(attendance) as stddev_attendance,
    min(attendance) as min_attendance,
    max(attendance) as max_attendance,

    -- 月別平均
    avg(case when month_value = 1 then attendance end) as jan_avg_attendance,
    avg(case when month_value = 2 then attendance end) as feb_avg_attendance,
    avg(case when month_value = 3 then attendance end) as mar_avg_attendance,
    avg(case when month_value = 4 then attendance end) as apr_avg_attendance,
    avg(case when month_value = 5 then attendance end) as may_avg_attendance,
    avg(case when month_value = 6 then attendance end) as jun_avg_attendance,
    avg(case when month_value = 7 then attendance end) as jul_avg_attendance,
    avg(case when month_value = 8 then attendance end) as aug_avg_attendance,
    avg(case when month_value = 9 then attendance end) as sep_avg_attendance,
    avg(case when month_value = 10 then attendance end) as oct_avg_attendance,
    avg(case when month_value = 11 then attendance end) as nov_avg_attendance,
    avg(case when month_value = 12 then attendance end) as dec_avg_attendance

  from game_datetime_enriched
  group by 1, 2, 3, 4
),

-- 15分単位の詳細分析
quarter_hour_analysis as (
  select
    hour_value,
    quarter_hour,
    quarter_hour_label,
    time_period_simple_jp,
    time_period_simple_en,

    count(distinct gameId) as total_games,
    sum(attendance) as total_attendance,
    avg(attendance) as avg_attendance,

    -- 週末と平日の比較
    avg(case when is_weekend then attendance end) as weekend_avg_attendance,
    avg(case when is_weekday then attendance end) as weekday_avg_attendance,

    count(distinct case when is_weekend then gameId end) as weekend_games,
    count(distinct case when is_weekday then gameId end) as weekday_games

  from game_datetime_enriched
  group by 1, 2, 3, 4, 5
),

-- 食事時間帯の分析
meal_time_analysis as (
  select
    case
      when is_breakfast_time then '朝食時間帯'
      when is_lunch_time then '昼食時間帯'
      when is_dinner_time then '夕食時間帯'
      else 'その他'
    end as meal_time_jp,

    case
      when is_breakfast_time then 'Breakfast Time'
      when is_lunch_time then 'Lunch Time'
      when is_dinner_time then 'Dinner Time'
      else 'Other'
    end as meal_time_en,

    count(distinct gameId) as total_games,
    sum(attendance) as total_attendance,
    avg(attendance) as avg_attendance,

    -- 年別推移
    count(distinct case when year_value = 2010 then gameId end) as games_2010,
    count(distinct case when year_value = 2011 then gameId end) as games_2011,
    count(distinct case when year_value = 2012 then gameId end) as games_2012,
    count(distinct case when year_value = 2013 then gameId end) as games_2013,
    count(distinct case when year_value = 2014 then gameId end) as games_2014,
    count(distinct case when year_value = 2015 then gameId end) as games_2015,
    count(distinct case when year_value = 2016 then gameId end) as games_2016,
    count(distinct case when year_value = 2017 then gameId end) as games_2017,
    count(distinct case when year_value = 2018 then gameId end) as games_2018,
    count(distinct case when year_value = 2019 then gameId end) as games_2019,
    count(distinct case when year_value = 2020 then gameId end) as games_2020

  from game_datetime_enriched
  where is_breakfast_time or is_lunch_time or is_dinner_time
  group by 1, 2
),

-- ラッシュアワー分析
rush_hour_analysis as (
  select
    case
      when is_morning_rush then '朝のラッシュ'
      when is_evening_rush then '夕方のラッシュ'
      when is_rush_hour then 'ラッシュアワー'
      else '通常時間'
    end as rush_hour_type_jp,

    case
      when is_morning_rush then 'Morning Rush'
      when is_evening_rush then 'Evening Rush'
      when is_rush_hour then 'Rush Hour'
      else 'Normal Hours'
    end as rush_hour_type_en,

    count(distinct gameId) as total_games,
    sum(attendance) as total_attendance,
    avg(attendance) as avg_attendance,
    avg(duration_minutes) as avg_duration

  from game_datetime_enriched
  group by 1, 2
)

-- 最終出力
select
  gde.game_schedule_sk,
  gde.gameId,
  gde.startTime,
  gde.game_date,

  -- 日付情報
  gde.year_value,
  gde.month_value,
  gde.month_name_jp,
  gde.month_name_en,
  gde.day_value,
  gde.day_name_jp,
  gde.day_name_en,
  gde.day_of_week,
  gde.week_of_year,
  gde.quarter_value,
  gde.is_weekend,
  gde.is_weekday,
  gde.fiscal_year_jp,
  gde.fiscal_quarter_jp,

  -- 時間情報
  gde.hour_value,
  gde.minute_value,
  gde.time_24h,
  gde.time_12h,
  gde.am_pm_jp,
  gde.am_pm,
  gde.time_period_jp,
  gde.time_period_en,
  gde.time_period_simple_jp,
  gde.time_period_simple_en,

  -- 時間フラグ
  gde.is_business_hours,
  gde.is_morning_rush,
  gde.is_evening_rush,
  gde.is_rush_hour,
  gde.is_breakfast_time,
  gde.is_lunch_time,
  gde.is_dinner_time,

  -- 時間グループ
  gde.quarter_hour,
  gde.quarter_hour_label,
  gde.half_hour,
  gde.half_hour_label,
  gde.five_minute_group,
  gde.ten_minute_group,

  -- ゲーム情報
  gde.homeTeamName,
  gde.awayTeamName,
  gde.attendance,
  gde.duration_minutes,
  gde.dayNight,
  gde.status,

  -- 派生メトリクス
  case
    when gde.attendance > 40000 then '超満員'
    when gde.attendance > 30000 then '満員'
    when gde.attendance > 20000 then '普通'
    else '少ない'
  end as attendance_category_jp,

  case
    when gde.attendance > 40000 then 'Packed'
    when gde.attendance > 30000 then 'Full'
    when gde.attendance > 20000 then 'Normal'
    else 'Low'
  end as attendance_category_en

from game_datetime_enriched gde
order by gde.startTime, gde.gameId
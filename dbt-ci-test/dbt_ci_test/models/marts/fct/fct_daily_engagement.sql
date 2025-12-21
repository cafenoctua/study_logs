{{
    config(
        materialized='table'
    )
}}

with events as (
    select * from {{ ref('stg_ga4__events') }}
),

daily_engagement as (
    select
        event_date,
        user_pseudo_id,
        sum(coalesce(engagement_time_msec, 0)) as total_engagement_time_msec,
        sum(coalesce(engagement_time_msec, 0)) / 1000.0 as total_engagement_time_sec,
        sum(coalesce(engagement_time_msec, 0)) / 1000.0 / 60.0 as total_engagement_time_min
    from events
    group by event_date, user_pseudo_id
)

select
    event_date,
    user_pseudo_id,
    total_engagement_time_msec,
    total_engagement_time_sec,
    total_engagement_time_min
from daily_engagement

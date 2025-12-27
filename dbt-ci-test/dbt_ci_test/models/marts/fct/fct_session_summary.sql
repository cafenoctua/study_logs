{{
    config(
        materialized='table'
    )
}}

with events as (
    select * from {{ ref('stg_ga4__events') }}
),

session_summary as (
    select
        event_date,
        user_pseudo_id,
        ga_session_id,
        min(event_timestamp) as session_start_time,
        max(event_timestamp) as session_end_time,
        count(*) as total_events,
        count(distinct event_name) as unique_event_types,
        count(distinct page_location) as pages_viewed,
        sum(coalesce(engagement_time_msec, 0)) as total_engagement_time_msec,
        max(case when event_name = 'purchase' then 1 else 0 end) as has_purchase,
        sum(coalesce(ecommerce_purchase_revenue, 0)) as session_revenue
    from events
    where ga_session_id is not null
    group by event_date, user_pseudo_id, ga_session_id
)

select
    event_date,
    user_pseudo_id,
    ga_session_id,
    session_start_time,
    session_end_time,
    timestamp_diff(session_end_time, session_start_time, second) as session_duration_seconds,
    total_events,
    unique_event_types,
    pages_viewed,
    total_engagement_time_msec,
    round(total_engagement_time_msec / 1000.0, 2) as total_engagement_time_seconds,
    has_purchase,
    session_revenue
from session_summary

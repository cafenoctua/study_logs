{{
    config(
        materialized='table'
    )
}}
-- CI trigger: 2025-12-21

with events as (
    select * from {{ ref('stg_ga4__events') }}
),

daily_access as (
    select
        event_date,
        user_pseudo_id,
        count(*) as total_events,
        count(distinct ga_session_id) as total_sessions,
        count(distinct page_location) as unique_pages_viewed
    from events
    group by event_date, user_pseudo_id
)

select
    event_date,
    user_pseudo_id,
    total_events,
    total_sessions,
    unique_pages_viewed
from daily_access

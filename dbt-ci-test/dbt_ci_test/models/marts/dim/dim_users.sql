{{
    config(
        materialized='table'
    )
}}

with events as (
    select * from {{ ref('stg_ga4__events') }}
),

users as (
    select
        user_pseudo_id,
        user_id,
        min(user_first_touch_timestamp) as first_touch_timestamp,
        min(event_date) as first_access_date
    from events
    group by user_pseudo_id, user_id
)

select
    user_pseudo_id,
    user_id,
    first_touch_timestamp,
    first_access_date
from users

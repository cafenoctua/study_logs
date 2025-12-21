{{
    config(
        materialized='table'
    )
}}

with events as (
    select * from {{ ref('stg_ga4__events') }}
),

users as (
    select * from {{ ref('dim_users') }}
),

daily_revenue as (
    select
        event_date,
        user_pseudo_id,
        sum(coalesce(ecommerce_purchase_revenue, 0)) as daily_revenue
    from events
    where ecommerce_purchase_revenue is not null
    group by event_date, user_pseudo_id
),

cumulative_ltv as (
    select
        dr.event_date,
        dr.user_pseudo_id,
        dr.daily_revenue,
        sum(dr.daily_revenue) over (
            partition by dr.user_pseudo_id
            order by dr.event_date
            rows between unbounded preceding and current row
        ) as cumulative_ltv
    from daily_revenue dr
)

select
    cl.event_date,
    cl.user_pseudo_id,
    u.first_access_date,
    date_diff(cl.event_date, u.first_access_date, day) as days_since_first_access,
    cl.daily_revenue,
    cl.cumulative_ltv
from cumulative_ltv cl
left join users u on cl.user_pseudo_id = u.user_pseudo_id

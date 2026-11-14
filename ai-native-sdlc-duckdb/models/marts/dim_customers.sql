-- 粒度: 1行 = 1顧客
with revenue as (
    select
        customer_id,
        count(*) as completed_orders,
        sum(amount) as lifetime_value,
        max(ordered_at) as last_ordered_at
    from {{ ref('fct_orders') }}
    where is_revenue
    group by customer_id
)

select
    c.customer_id,
    c.customer_name,
    c.signup_date,
    c.country,
    coalesce(r.completed_orders, 0) as completed_orders,
    coalesce(r.lifetime_value, 0) as lifetime_value,
    r.last_ordered_at
from {{ ref('stg_customers') }} as c
left join revenue as r on c.customer_id = r.customer_id

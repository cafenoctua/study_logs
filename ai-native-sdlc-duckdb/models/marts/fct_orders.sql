-- 粒度: 1行 = 1注文
select
    o.order_id,
    o.customer_id,
    o.ordered_at,
    cast(o.ordered_at as date) as order_date,
    o.amount,
    o.status,
    o.status = 'completed' as is_revenue
from {{ ref('stg_orders') }} as o

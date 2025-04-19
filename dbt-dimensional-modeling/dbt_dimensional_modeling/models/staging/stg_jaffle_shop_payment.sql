with
import_customers as (
  select * from {{ ref('raw_customers') }}
),

import_orders as (
  select * from {{ ref('raw_orders') }}
  where true
    {% if not(var('first_run')) %}
    and order_date = '{{ var('date') }}'
    {% endif %}
),

import_payments as (
  select * from {{ ref('raw_payments') }}
),

final as (
  select
    import_orders.order_date,
    import_orders.user_id,
    import_customers.first_name,
    case
      when
        import_orders.order_date = "2018-02-10"
        and import_customers.last_name = "P."
      then "W."
      when
        import_orders.order_date = "2018-01-01"
        and import_customers.last_name = "P."
        and {{ var('first_run') }}
      then
        null
      else import_customers.last_name
    end as last_name,
    import_payments.order_id,
    import_orders.status,
    import_payments.payment_method,
    import_payments.amount
  from
    import_orders
  inner join
    import_customers
  on
    import_orders.user_id = import_customers.id
  inner join
    import_payments
  on
    import_orders.id = import_payments.order_id
)

select * from final
{% if var('retry') %}
{# insert correct source data #}
union all
select
  date("2018-02-09") as order_date,
  1 as user_id,
  'Michael' as fist_name,
  'M.' as last_name,
  1 as order_id,
  cast(null as string) as status,
  cast(null as string) as payment_method,
  0 as amount 
{% endif %}
with
tl as (
  select * from {{ ref('t_link_transactions') }}
),

hc as (
  select * from {{ ref('hub_customer') }}
),

ho as (
  select * from {{ ref('hub_order') }}
),

sc as (
  select
    *
  from
    {{ ref('sat_order_customer_details') }} as sc
  where
    load_date = (select max(load_date) from {{ ref('sat_order_customer_details') }})
),

sn as (
  select *
  from
    {{ ref('sat_order_cust_nation_details') }}
  where
    load_date = (select max(load_date) from {{ ref('sat_order_cust_nation_details') }})
),

so as (
  select
    *
  from
    {{ ref('sat_order_order_details') }} as so
  where
    load_date = (select max(load_date) from {{ ref('sat_order_order_details') }})
)

select
  -- sc.CUSTOMER_NAME,
  -- sc.CUSTOMER_ADDRESS,
  so.ORDERDATE,
  sn.CUSTOMER_NATION_NAME,
  so.ORDERSTATUS,
  {# sum(so.TOTALPRICE) #}
  tl.TRANSACTION_DATE,
  tl.TYPE,
  tl.AMOUNT
from
  tl
inner join
  hc
on
  tl.CUSTOMER_PK = hc.CUSTOMER_PK
inner join
  ho
on
  tl.ORDER_PK = ho.ORDER_PK
inner join
  sc
on
  hc.CUSTOMER_PK = sc.CUSTOMER_PK
inner join
  sn
on
  hc.CUSTOMER_PK = sn.CUSTOMER_PK
inner join
  so
on
  ho.ORDER_PK = so.ORDER_PK
{# group by 1, 2, 3
order by 4 desc #}
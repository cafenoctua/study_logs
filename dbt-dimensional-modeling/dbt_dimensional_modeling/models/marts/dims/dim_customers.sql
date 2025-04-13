with
import_stg_payment as (
  select
    order_date,
    user_id,
    first_name,
    last_name
  from {{ ref('stg_jaffle_shop_payment') }}
),

new_records as (
  select
    * except (order_date),
    {{
      generate_hash_value([
        'first_name',
        'last_name'
      ])
    }} as hash_value,
    timestamp(min(order_date)) as valid_from,
    timestamp("9999-12-31") as valid_to,
    false as is_current
  from
    import_stg_payment
  group by all
),

{%- if not(var('retry')) %}

{% if is_incremental() %}
current_records as (
  select *
  from
    {{ this }}
  where
    is_current is true
),
{% endif %}

filter_new_records as (
  select *
  from
    new_records
  where true
  {% if is_incremental() %}
  and hash_value not in (select hash_value from current_records)
  {% endif %}
),

union_records as (
  select
    dense_rank() over (
      order by valid_from, user_id
    )
    {%- if is_incremental() -%}
      + (select max(customer_sk) from current_records)
    {%- endif -%}
    as customer_sk,
    *,
  from
    filter_new_records
  {% if is_incremental() %}
    union all
    select * from current_records
  {% endif %}
),

insert_records as (
  select
    * except (valid_to, is_current),
    coalesce(
      timestamp_sub(
        lead(valid_from) over (
          partition by user_id
          order by valid_from
        ), interval 1 second)
    , valid_to) as valid_to,
    case
      when
        lead(valid_from) over (
          partition by user_id
          order by valid_from
        ) is null
      then true
      else false
    end as is_current
  from
    union_records
),

{% else %}
{# 
この処理で過去のソースが修正されたものを再処理したときに有効期限の整合性はとれる
次なる課題は新規挿入された過去データがそれ以降とデータとattributeが同一の場合有効期限が違うが同一のhash_valueを持つレコードが重複する
使うデータ自体に不都合は出ないが有効期限の振る舞いで怪しい形になる
#}
historical_records as (
  select *
  from
    {{ this }}
  where
    valid_from >= '{{ var('date') }}'
),

correct_records as (
  select
    historical_records.customer_sk,
    new_records.* except (valid_from, valid_to, is_current),
    historical_records.valid_from,
    historical_records.valid_to,
    historical_records.is_current,
  from
    new_records
  left join
    historical_records
  on
    new_records.user_id = historical_records.user_id
    and new_records.valid_from = historical_records.valid_from
  where
    historical_records.user_id is not null
    and new_records.hash_value <> historical_records.hash_value
),

filter_new_records as (
  select new_records.*
  from
    new_records
  left join
    historical_records
  on
    new_records.user_id = historical_records.user_id
    and new_records.valid_from = historical_records.valid_from
  where
    historical_records.user_id is null
),

union_records as (
  select
    dense_rank() over (
      order by valid_from, user_id
    ) + (select max(customer_sk) from {{ this }} where is_current = true) as customer_sk,
    *
  from
    filter_new_records
  union all
  select * from correct_records
  union all
  select * from historical_records where customer_sk not in (select customer_sk from correct_records)
),

insert_records as (
  select
    * except (valid_to, is_current),
    coalesce(
      timestamp_sub(
        lead(valid_from) over (
          partition by user_id
          order by valid_from
        ), interval 1 second)
    , valid_to) as valid_to,
    case
      when
        lead(valid_from) over (
          partition by user_id
          order by valid_from
        ) is null
      then true
      else false
    end as is_current
  from
    union_records
),

{% endif %}


final as (
  select *
  from
    insert_records
)

select
  *
from
  final
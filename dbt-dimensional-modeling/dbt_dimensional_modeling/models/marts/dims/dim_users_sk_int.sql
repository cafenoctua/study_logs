with
import_stg_ga as (
  select
    fullVisitorId as visitor_id,
    geoNetwork.continent as continent,
    geoNetwork.subContinent as sub_continent,
    geoNetwork.country as country,
    device.browser as browser,
    device.operatingSystem as os,
    device.deviceCategory as device_category,
    device.isMobile as is_mobile,
    {{ generate_hash_value(['geoNetwork.continent', 'geoNetwork.subContinent', 'geoNetwork.country ', 'device.browser', 'device.operatingSystem', 'device.deviceCategory', 'device.isMobile']) }} as hash_value,
    access_timestamp
  from {{ ref('stg_ga_sample') }} 
),

{% if is_incremental() %}  
get_latest_dim as (
  select
    *,
  from {{ this }}
  where
    is_current = true
),
{% endif %}

today_data as (
  select
    * except (access_timestamp),
    access_timestamp as valid_from,
    timestamp("9999-12-31") as valid_to,
    false as is_current,
  from
    import_stg_ga
  {% if is_incremental() %}
  union all
  select * except (user_sk) from get_latest_dim
  {% endif %}
),

new_data as (
  select
    *,
    lag(hash_value) over (
      partition by visitor_id
      order by valid_from asc
    ) as lag_hash_value,
  from
    today_data
  qualify
    is_current = false
    and (
      hash_value <> lag_hash_value
      or lag_hash_value is null
    )
),

calc_user_sk as (
  select
    dense_rank() over (
      order by valid_from, visitor_id
    )
    {%- if is_incremental() -%}
      + (select max(user_sk) from get_latest_dim)
    {%- endif -%}
    as user_sk,
    * except (lag_hash_value)
  from
    new_data
  {%- if is_incremental() %}
    union all
    select *
    from
      get_latest_dim
  {%- endif -%}
),

insert_data as (
  select
    * except (valid_to, is_current),
    coalesce(timestamp_sub(lead(valid_from) over (
      partition by visitor_id
      order by valid_from
    ), interval 1 second), valid_to) as valid_to,
    case
      when
        lead(valid_from) over (
          partition by visitor_id
          order by valid_from
        ) is null then true
      else false
    end as is_current
  from
    calc_user_sk
),

final as (
  select *
  from
    insert_data
)

select *
from
  final
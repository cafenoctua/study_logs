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


new_data as (
  select
    * except (access_timestamp),
    access_timestamp as valid_from,
    timestamp("9999-12-31") as valid_to,
    false as is_current,
  from
    import_stg_ga
),

get_diff_data as (
  select
    *,
    lag(hash_value) over (
      partition by visitor_id
      order by valid_from asc
    ) as lag_hash_value,
  from
    new_data
  qualify
    hash_value <> lag_hash_value
    or lag_hash_value is null
),

insert_data as (
  select
    * except (valid_to, is_current, lag_hash_value),
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
    get_diff_data
),

final as (
  select
    dense_rank() over (
      order by valid_from, visitor_id
    ) as user_sk,
    *
  from
    insert_data
)

select *
from
  final
order by user_sk
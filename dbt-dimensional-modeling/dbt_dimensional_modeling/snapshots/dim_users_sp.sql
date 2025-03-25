{% snapshot dim_users_sp %}

{{
   config(
      target_database='sweepsump',
      target_schema='dbt_dimensional_modeling',
      unique_key='visitor_id',
      strategy='check',
      check_cols=['hash_value']
   )
}}

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
    access_timestamp
  from {{ ref('stg_ga_sample') }} 
),

set_hash_value as (
  select
    *,
    {{ dbt_utils.generate_surrogate_key(['continent', 'sub_continent', 'country', 'browser', 'os', 'device_category', 'is_mobile']) }} as hash_value
  from
    import_stg_ga
)

select *
from
  set_hash_value

{% endsnapshot %}
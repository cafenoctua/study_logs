{{
    config(
        materialized='table'
    )
}}

with events as (
    select * from {{ ref('stg_ga4__events') }}
),

devices as (
    select distinct
        device_category,
        device_os,
        device_os_version,
        device_browser,
        device_browser_version,
        device_language
    from events
    where device_category is not null
)

select
    {{ dbt_utils.generate_surrogate_key(['device_category', 'device_os', 'device_os_version', 'device_browser', 'device_browser_version']) }} as device_key,
    device_category,
    device_os,
    device_os_version,
    device_browser,
    device_browser_version,
    device_language
from devices

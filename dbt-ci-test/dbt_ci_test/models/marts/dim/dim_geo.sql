{{
    config(
        materialized='table'
    )
}}

with events as (
    select * from {{ ref('stg_ga4__events') }}
),

geo as (
    select distinct
        geo_continent,
        geo_country,
        geo_region,
        geo_city
    from events
    where geo_country is not null
)

select
    {{ dbt_utils.generate_surrogate_key(['geo_continent', 'geo_country', 'geo_region', 'geo_city']) }} as geo_key,
    geo_continent,
    geo_country,
    geo_region,
    geo_city
from geo

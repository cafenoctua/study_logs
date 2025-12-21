{{
    config(
        materialized='table'
    )
}}

with events as (
    select * from {{ ref('stg_ga4__events') }}
),

apps as (
    select distinct
        app_id,
        app_version,
        firebase_app_id
    from events
    where app_id is not null or firebase_app_id is not null
)

select
    {{ dbt_utils.generate_surrogate_key(['app_id', 'app_version', 'firebase_app_id']) }} as app_key,
    app_id,
    app_version,
    firebase_app_id
from apps

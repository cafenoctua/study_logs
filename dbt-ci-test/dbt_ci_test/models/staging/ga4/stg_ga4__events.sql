{{
    config(
        materialized='view'
    )
}}
-- CI trigger: 2024-12-21

with source as (
    select * from {{ source('ga4_ecommerce', 'events') }}
),

renamed as (
    select
        -- 日付・時間
        parse_date('%Y%m%d', event_date) as event_date,
        timestamp_micros(event_timestamp) as event_timestamp,

        -- イベント情報
        event_name,

        -- ユーザー情報
        user_id,
        user_pseudo_id,
        timestamp_micros(user_first_touch_timestamp) as user_first_touch_timestamp,

        -- デバイス情報
        device.category as device_category,
        device.operating_system as device_os,
        device.operating_system_version as device_os_version,
        device.web_info.browser as device_browser,
        device.web_info.browser_version as device_browser_version,
        device.language as device_language,
        device.is_limited_ad_tracking as device_is_limited_ad_tracking,
        device.mobile_brand_name as device_mobile_brand_name,
        device.mobile_model_name as device_mobile_model_name,

        -- 地理情報
        geo.continent as geo_continent,
        geo.country as geo_country,
        geo.region as geo_region,
        geo.city as geo_city,

        -- アプリケーション情報
        app_info.id as app_id,
        app_info.version as app_version,
        app_info.firebase_app_id as firebase_app_id,

        -- イベントパラメータ（よく使うものを抽出）
        (select value.int_value from unnest(event_params) where key = 'engagement_time_msec') as engagement_time_msec,
        (select value.int_value from unnest(event_params) where key = 'ga_session_id') as ga_session_id,
        (select value.int_value from unnest(event_params) where key = 'ga_session_number') as ga_session_number,
        (select value.string_value from unnest(event_params) where key = 'page_location') as page_location,
        (select value.string_value from unnest(event_params) where key = 'page_title') as page_title,

        -- Eコマース情報
        ecommerce.total_item_quantity as ecommerce_total_item_quantity,
        ecommerce.purchase_revenue as ecommerce_purchase_revenue,
        ecommerce.transaction_id as ecommerce_transaction_id

    from source
)

select * from renamed

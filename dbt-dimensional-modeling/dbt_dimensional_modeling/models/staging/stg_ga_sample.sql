with
import_raw as (
    select
        parse_date("%Y%m%d", _TABLE_SUFFIX) as transaction_date,
        *
    from
        {{ source('google_analytics_sample', 'ga_sessions_*') }}
),

final as (
    select *
    from
        import_raw
)

select *
from
    final
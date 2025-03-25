with
import_raw as (
  select
    parse_date("%Y%m%d", _TABLE_SUFFIX) as transaction_date,
    timestamp_seconds(visitStartTime) as access_timestamp,
    *
  from
    {{ source('google_analytics_sample', 'ga_sessions_*') }}
  where
    _TABLE_SUFFIX = "{{ var('date') }}"
),

final as (
  select *
  from
    import_raw
)

select *
from
  final
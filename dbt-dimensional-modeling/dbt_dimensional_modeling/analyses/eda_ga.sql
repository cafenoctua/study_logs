select
  count(distinct fullVisitorId)
from
  {{ source('google_analytics_sample', 'ga_sessions_*') }}
where
  REGEXP_CONTAINS(_TABLE_SUFFIX, r'^201608(0[1-9]|1[0-5])$') = true
{# group by 1,2
order by 3 desc #}
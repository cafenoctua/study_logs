with
import_stg_ga as (
  select * from {{ ref('stg_ga_sample') }}
),

import_dim_users as (
  select * from {{ ref('dim_users_sk_int') }}
),

final as (
  select
    import_dim_users.user_sk,
    import_stg_ga.transaction_date,
    import_stg_ga.access_timestamp,
    if(totals.newVisits is null, false, true) as is_new_visits,
    totals.visits as visits,
    totals.hits as hits,
    totals.pageviews as pageviews,
    totals.timeOnSite as time_on_site
  from
    import_stg_ga
  left join
    import_dim_users
  on
    import_stg_ga.fullVisitorId = import_dim_users.visitor_id
    and import_stg_ga.access_timestamp between import_dim_users.valid_from and import_dim_users.valid_to
)

select *
from
  final
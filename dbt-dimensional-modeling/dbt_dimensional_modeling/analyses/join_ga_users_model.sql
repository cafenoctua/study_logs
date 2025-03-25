with
dim_users as (
  select * from {{ ref('dim_users') }}
),

fct_visits as (
  select * from {{ ref('fct_visits') }}
),

join_visits as (
  select
    dim_users.visitor_id,
    dim_users.continent,
    dim_users.sub_continent,
    dim_users.country,
    dim_users.browser,
    dim_users.os,
    dim_users.device_category,
    dim_users.is_mobile,
    fct_visits.transaction_date,
    fct_visits.access_timestamp,
    fct_visits.is_new_visits,
    fct_visits.visits,
    fct_visits.hits,
    fct_visits.pageviews,
    fct_visits.time_on_site
  from
    fct_visits
  join
    dim_users
  on
    fct_visits.user_sk = dim_users.user_sk
)

select
  continent,
  sub_continent,
  sum(visits) as visit_num,
  sum(hits) as hit_num
from
  join_visits
group by 1, 2
order by 3 desc, 4 desc
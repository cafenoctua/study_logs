select
  user_sk,
  count(*)
from
  {{ ref('dim_users_sk_int') }}
group by 1
order by 2 desc, 1 desc
select 
b.* except (user_sk),
a.* except (user_sk)
from
  {{ ref('fct_visits_sk_int') }} as a
inner join
  {{ ref('dim_users_sk_int') }} as b
on
  a.user_sk = b.user_sk
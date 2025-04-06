select 
b.* except (user_sk),
a.* except (user_sk)
from
  {{ ref('fct_visits') }} as a
inner join
  {{ ref('dim_users') }} as b
on
  a.user_sk = b.user_sk
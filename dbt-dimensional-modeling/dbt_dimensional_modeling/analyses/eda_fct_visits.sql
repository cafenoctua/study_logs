select *
from
  {{ ref('fct_visits') }}
where
  user_sk is not null
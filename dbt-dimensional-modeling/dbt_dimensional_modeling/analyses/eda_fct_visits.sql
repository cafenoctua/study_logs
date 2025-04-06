select
  count(*)
from
  {{ ref('fct_visits_sk_int') }}
{# where
  user_sk is not null #}
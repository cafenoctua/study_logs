select
  *
from
  {{ ref('dim_customers') }}
where
  user_id = 1
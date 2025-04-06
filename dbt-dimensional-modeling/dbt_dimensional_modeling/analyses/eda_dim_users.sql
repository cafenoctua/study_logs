select 
  {# visitor_id,
  count(*) #}
  {# * #}
  count(*)
from
  {{ ref('dim_users_sk_int') }}
{# where
  date(valid_from) <= "2016-08-03"  #}
{# where
  visitor_id = "2040429609628789402" #}
{# group by 1
order by 2 desc #}
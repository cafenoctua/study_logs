with
import_schedules as (
select
  *
from
  `bigquery-public-data.baseball.schedules`
)

select *
from import_schedules
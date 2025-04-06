#!/bin/bash

start_date=20160801
end_date=20160831

current_date=$start_date

while [ "$current_date" -le "$end_date" ]; do
  echo "$current_date"
  if [ $current_date -eq $start_date ]; then
    echo full refresh
    uv run dbt run -f --project-dir dbt_dimensional_modeling --vars '{"date": "'${start_date}'"}'
  else
    uv run dbt run --project-dir dbt_dimensional_modeling --vars '{"date": "'${current_date}'"}'
  fi
  current_date=$(date -d "$current_date +1 day" +"%Y%m%d")
done
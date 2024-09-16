WITH as_of_date AS (
    {{ dbt_utils.date_spine("day", "date('1992-01-08')", "date('1992-01-11')") }}
)

SELECT date_day as AS_OF_DATE FROM as_of_date
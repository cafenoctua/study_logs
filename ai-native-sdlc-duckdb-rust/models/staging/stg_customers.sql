select
    customer_id,
    name as customer_name,
    cast(signup_date as date) as signup_date,
    country
from {{ ref('raw_customers') }}

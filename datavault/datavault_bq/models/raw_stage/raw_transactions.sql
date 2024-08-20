SELECT
    b.O_ORDERKEY AS ORDER_ID,
    b.O_CUSTKEY AS CUSTOMER_ID,
    b.O_ORDERDATE AS ORDER_DATE,
    date_add(b.O_ORDERDATE, interval 20 DAY) AS TRANSACTION_DATE,
    concat(b.O_ORDERKEY, b.O_CUSTKEY, format_date('YYYYMMDD', b.O_ORDERDATE))
    || substr(FORMAT('%023d', 0),
        length(concat(b.O_ORDERKEY, b.O_CUSTKEY, format_date('YYYYMMDD', b.O_ORDERDATE)))
    ) AS TRANSACTION_NUMBER,
    'DUMMY' as DUMMY_COLS,
    b.O_TOTALPRICE AS AMOUNT,
    CASE abs(MOD(cast(rand() * 10 as int64), 2)) + 1
        WHEN 1 THEN 'DR'
        WHEN 2 THEN 'CR'
    END AS TYPE
FROM {{ source('tpch_sample', 'order') }}  AS b
LEFT JOIN {{ source('tpch_sample', 'customer') }} AS c
    ON b.O_CUSTKEY = c.C_CUSTKEY
WHERE b.O_ORDERDATE = date('{{ var('load_date') }}')
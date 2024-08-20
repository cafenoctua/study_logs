

-- Generated by AutomateDV (formerly known as dbtvault)

    

WITH source_data AS (
    SELECT a.ORDER_CUSTOMER_PK, a.ORDER_PK, a.CUSTOMER_PK, a.SHIPDATE, a.COMMITDATE, a.EFFECTIVE_FROM, a.LOAD_DATE, a.RECORD_SOURCE
    FROM `sweepsump`.`tpch_sf10_test`.`v_stg_orders` AS a
    WHERE a.ORDER_PK IS NOT NULL
    AND a.CUSTOMER_PK IS NOT NULL
),

latest_records AS (
    SELECT * FROM (
        SELECT b.ORDER_CUSTOMER_PK, b.ORDER_PK, b.CUSTOMER_PK, b.SHIPDATE, b.COMMITDATE, b.EFFECTIVE_FROM, b.LOAD_DATE, b.RECORD_SOURCE,
               ROW_NUMBER() OVER (
                    PARTITION BY b.ORDER_CUSTOMER_PK
                    ORDER BY b.LOAD_DATE DESC
               ) AS row_num
        FROM `sweepsump`.`tpch_sf10_test`.`eff_sat_order_customer` AS b
    )AS inner_rank
        WHERE row_num = 1),

latest_open AS (
    SELECT c.ORDER_CUSTOMER_PK, c.ORDER_PK, c.CUSTOMER_PK, c.SHIPDATE, c.COMMITDATE, c.EFFECTIVE_FROM, c.LOAD_DATE, c.RECORD_SOURCE
    FROM latest_records AS c
    WHERE DATE(c.COMMITDATE) = DATE(PARSE_DATETIME('%F %H:%M:%E6S', '9999-12-31 23:59:59.999999'))
),

latest_closed AS (
    SELECT d.ORDER_CUSTOMER_PK, d.ORDER_PK, d.CUSTOMER_PK, d.SHIPDATE, d.COMMITDATE, d.EFFECTIVE_FROM, d.LOAD_DATE, d.RECORD_SOURCE
    FROM latest_records AS d
    WHERE DATE(d.COMMITDATE) != DATE(PARSE_DATETIME('%F %H:%M:%E6S', '9999-12-31 23:59:59.999999'))
),

new_open_records AS (
    SELECT DISTINCT
        f.ORDER_CUSTOMER_PK,
        f.ORDER_PK, f.CUSTOMER_PK,
        
        f.SHIPDATE AS SHIPDATE,
        
        f.COMMITDATE AS COMMITDATE,
        f.EFFECTIVE_FROM AS EFFECTIVE_FROM,
        f.LOAD_DATE,
        f.RECORD_SOURCE
    FROM source_data AS f
    LEFT JOIN latest_records AS lr
    ON f.ORDER_CUSTOMER_PK = lr.ORDER_CUSTOMER_PK
    WHERE lr.ORDER_CUSTOMER_PK IS NULL
),

new_reopened_records AS (
    SELECT DISTINCT
        lc.ORDER_CUSTOMER_PK,
        lc.ORDER_PK, lc.CUSTOMER_PK,
        
        g.SHIPDATE AS SHIPDATE,
        
        g.COMMITDATE AS COMMITDATE,
        g.EFFECTIVE_FROM AS EFFECTIVE_FROM,
        g.LOAD_DATE,
        g.RECORD_SOURCE
    FROM source_data AS g
    INNER JOIN latest_closed AS lc
    ON g.ORDER_CUSTOMER_PK = lc.ORDER_CUSTOMER_PK
    WHERE DATE(g.COMMITDATE) = DATE(PARSE_DATETIME('%F %H:%M:%E6S', '9999-12-31 23:59:59.999999'))
),

new_closed_records AS (
    SELECT DISTINCT
        lo.ORDER_CUSTOMER_PK,
        lo.ORDER_PK, lo.CUSTOMER_PK,
        h.SHIPDATE AS SHIPDATE,
        h.COMMITDATE AS COMMITDATE,
        h.EFFECTIVE_FROM AS EFFECTIVE_FROM,
        h.LOAD_DATE,
        lo.RECORD_SOURCE
    FROM source_data AS h
    LEFT JOIN latest_open AS lo
    ON lo.ORDER_CUSTOMER_PK = h.ORDER_CUSTOMER_PK
    LEFT JOIN latest_closed AS lc
    ON lc.ORDER_CUSTOMER_PK = h.ORDER_CUSTOMER_PK
    WHERE DATE(h.COMMITDATE) != DATE(PARSE_DATETIME('%F %H:%M:%E6S', '9999-12-31 23:59:59.999999'))
    AND lo.ORDER_CUSTOMER_PK IS NOT NULL
    AND lc.ORDER_CUSTOMER_PK IS NULL
),

records_to_insert AS (
    SELECT * FROM new_open_records
    UNION DISTINCT
    SELECT * FROM new_reopened_records
    UNION DISTINCT
    SELECT * FROM new_closed_records
)

SELECT * FROM records_to_insert
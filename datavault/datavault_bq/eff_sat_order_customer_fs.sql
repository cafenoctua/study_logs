

-- Generated by AutomateDV (formerly known as dbtvault)

    

WITH source_data AS (
    SELECT a.ORDER_CUSTOMER_PK, a.ORDER_PK, a.CUSTOMER_PK, a.SHIPDATE, a.COMMITDATE, a.EFFECTIVE_FROM, a.LOAD_DATE, a.RECORD_SOURCE
    FROM `sweepsump`.`tpch_sf10_test`.`v_stg_orders` AS a
    WHERE a.ORDER_PK IS NOT NULL
    AND a.CUSTOMER_PK IS NOT NULL
),

records_to_insert AS (
    SELECT i.ORDER_CUSTOMER_PK, i.ORDER_PK, i.CUSTOMER_PK, i.SHIPDATE, i.COMMITDATE, i.EFFECTIVE_FROM, i.LOAD_DATE, i.RECORD_SOURCE
    FROM source_data AS i
)

SELECT * FROM records_to_insert
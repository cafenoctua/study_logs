{%- set yaml_metadata -%}
source_model: v_stg_orders
src_pk: ORDER_CUSTOMER_PK
src_dfk:
  - ORDER_PK
src_sfk: CUSTOMER_PK
src_start_date: SHIPDATE
src_end_date: COMMITDATE
src_eff: EFFECTIVE_FROM
src_ldts: LOAD_DATE
src_source: RECORD_SOURCE
{%- endset -%}

{% set metadata_dict = fromyaml(yaml_metadata) %}

{{ automate_dv.eff_sat(src_pk=metadata_dict["src_pk"],
                      src_dfk=metadata_dict["src_dfk"],
                      src_sfk=metadata_dict["src_sfk"],
                      src_start_date=metadata_dict["src_start_date"],
                      src_end_date=metadata_dict["src_end_date"],
                      src_eff=metadata_dict["src_eff"],
                      src_ldts=metadata_dict["src_ldts"],
                      src_source=metadata_dict["src_source"],
                      source_model=metadata_dict["source_model"])}} 
{%- set yaml_metadata -%}
source_model: v_stg_orders
src_pk: CUSTOMER_PK
src_cdk:
  - CUSTOMER_PHONE
src_payload:
  - CUSTOMER_NAME
src_hashdiff: CUSTOMER_HASHDIFF
src_eff: EFFECTIVE_FROM
src_ldts: LOAD_DATETIME
src_source: RECORD_SOURCE
{%- endset -%}

{% set metadata_dict = fromyaml(yaml_metadata) %}

{{ automate_dv.ma_sat(src_pk=metadata_dict["src_pk"],
                      src_cdk=metadata_dict["src_cdk"],
                      src_payload=metadata_dict["src_payload"],
                      src_hashdiff=metadata_dict["src_hashdiff"],
                      src_eff=metadata_dict["src_eff"],
                      src_ldts=metadata_dict["src_source"],
                      source_model=metadata_dict["source_model"])}}

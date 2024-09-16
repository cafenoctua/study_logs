{%- set yaml_metadata -%}
source_model: hub_customer
src_pk: CUSTOMER_PK
as_of_dates_table: as_of_date
satellites: 
  sat_order_customer_details:
    pk:
      PK: CUSTOMER_PK
    ldts:
      LDTS: LOAD_DATE
  sat_order_cust_nation_details:
    pk:
      PK: CUSTOMER_PK
    ldts:
      LDTS: LOAD_DATE
stage_tables_ldts:
  sat_order_customer_details: LOAD_DATE
  sat_order_cust_nation_details: LOAD_DATE
src_ldts: LOAD_DATE
{%- endset -%}

{% set metadata_dict = fromyaml(yaml_metadata) %}

{{ automate_dv.pit(source_model=metadata_dict['source_model'], 
                   src_pk=metadata_dict['src_pk'],
                   as_of_dates_table=metadata_dict['as_of_dates_table'],
                   satellites=metadata_dict['satellites'],
                   stage_tables_ldts=metadata_dict['stage_tables_ldts'],
                   src_ldts=metadata_dict['src_ldts']) }}
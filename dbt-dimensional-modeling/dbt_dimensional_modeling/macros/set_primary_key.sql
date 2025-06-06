{% macro set_primary_key(pk_cols) %}
  {%- if should_full_refresh() -%}
  alter table {{ schema }}.{{ model.name }} add primary key (
    {%- for pk_col in pk_cols -%}
      {{ pk_col }}
      {%- if not loop.last -%}
      ,
      {%- endif -%}
    {%- endfor -%}
  ) not enforced
  {%- endif -%}
{% endmacro %}
{% macro set_foreign_key(fk_configs) %}
  {%- if should_full_refresh() -%}
  alter table {{ schema }}.{{ model.name }}
  {% for fk_config in fk_configs -%}
  add foreign key (
    {{ fk_config.fk_col }}
  ) references {{ schema }}.{{ fk_config.fk_model }}({{ fk_config.fk_col }}) not enforced
  {%- endfor -%}
  {%- endif -%}
{% endmacro %}
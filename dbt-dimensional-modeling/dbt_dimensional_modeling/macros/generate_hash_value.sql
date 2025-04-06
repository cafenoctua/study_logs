{%- macro generate_hash_value(field_list) -%}

{%- set fields = [] -%}
{%- for field in field_list -%}
  {%- do fields.append(
    "coalesce(cast(" ~  field ~ " as string), '')"
  ) -%}
  {%- if not loop.last -%}
    {%- do fields.append("'-'") -%}
  {%- endif -%}
{%- endfor -%}
to_base64(sha256(concat({%- for field in fields -%}
  {{ field }}
  {%- if not loop.last -%}
  ,
  {%- endif -%}
{%- endfor -%})))
{%- endmacro -%}
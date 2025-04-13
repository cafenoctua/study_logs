deps:
	cd dbt_dimensional_modeling \
	&& dbt deps

genpub:
	cd dbt_dimensional_modeling \
	&& dbt \
		--quiet \
		run-operation \
		generate_source \
		--args '{"database_name": "bigquery-public-data", "schema_name": "$(DATASET)", "case_sensitive_databases": true, "case_sensitive_schemas": true, "case_sensitive_tables": true}' \
		> models/sources/_source_$(DATASET).yml

osm:
	cd dbt_dimensional_modeling \
	&& uv run dbt-osmosis yaml refactor --profiles-dir ../profiles

run-dates:
	sh ./scripts/run-dates.sh

frun:
	dbt run -fs +dim_customers --project-dir dbt_dimensional_modeling/ --vars '{date: 2018-01-01, first_run: true}'

run:
	dbt run -s +dim_customers --project-dir dbt_dimensional_modeling/ --vars '{date: 2018-01-01, first_run: false, retry: true}'

run-stg:
	dbt run -s stg_jaffle_shop_payment --project-dir dbt_dimensional_modeling/ --vars '{date: 2018-01-01, first_run: false, retry: true}'

compile:
	dbt compile -s dim_customers --project-dir dbt_dimensional_modeling/ --vars '{date: 2018-01-01, first_run: false, retry: true}'

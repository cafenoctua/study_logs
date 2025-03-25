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
	&& dbt-osmosis yaml refactor --profiles-dir ../profiles

run-dates:
	sh ./scripts/run-dates.sh
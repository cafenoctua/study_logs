# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a dbt project implementing calendar dimensions for data warehouse dimensional modeling. The project uses dbt Fusion engine with BigQuery as the data warehouse.

## Essential Commands

```bash
# Build all models (use dbtf instead of dbt for Fusion engine)
dbtf build

# Run models only
dbtf run

# Run tests only
dbtf test

# Compile SQL without executing
dbtf compile

# Install package dependencies
dbtf deps

# Run specific model
dbtf run --select dim_calendar

# Run staging models only
dbtf run --select staging

# Debug connection
dbtf debug
```

## Architecture and Conventions

### Data Sources
- **BigQuery Public Data**: `bigquery-public-data.baseball.*`
  - `schedules`: Baseball game schedules
  - `games_wide`: Game statistics
  - `games_post_wide`: Post-season game data

### Model Organization

```
models/
├── staging/              # Data cleansing (materialized as views)
│   └── stg_*.sql        # Naming: stg_{source_name}.sql
├── marts/
│   ├── dim/             # Dimensions (materialized as tables)
│   │   └── dim_*.sql    # Naming: dim_{dimension_name}.sql
│   ├── fact/            # Facts (materialized as tables)
│   │   └── fct_*.sql    # Naming: fct_{fact_name}.sql
│   └── analytics/       # Analysis-ready data marts
│       └── anl_*.sql    # Naming: anl_{mart_name}.sql
```

### Key Design Patterns

1. **Surrogate Keys**:
   - Use integer type surrogate keys for all dimension-fact relationships
   - Column naming: `*_sk` (e.g., `calendar_sk`, `team_sk`)
   - Generate using sequential integers or hash functions

2. **Calendar Dimension (`dim_calendar`)**:
   - Covers 2010-2020 date range
   - Includes: date components, quarters, week numbers, weekend flags
   - Integer date formats: `date_int` (YYYYMMDD), `year_month_int` (YYYYMM)
   - Uses recursive CTEs for date generation

3. **SQL Dialect**: BigQuery SQL
   - Use `cast()` for type conversions
   - `lpad()` for zero-padding
   - `extract()` for date parts
   - `generate_series()` for sequences

### Database Configuration
- **Profile**: `time_calendar_dim` (configured in `~/.dbt/profiles.yml`)
- **Target**: BigQuery
- **Schema Strategy**: Seeds use `_raw` suffix, models use default schema

## Development Notes

- Always use `dbtf` command instead of `dbt` (Fusion engine requirement)
- BigQuery SQL syntax required for all models
- Test models with `dbtf compile` before running
- Check compiled SQL in `target/compiled/` directory for debugging
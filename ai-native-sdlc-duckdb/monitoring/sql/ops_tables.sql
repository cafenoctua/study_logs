-- ops スキーマ(warehouse/prod.duckdb 内)。BigQuery 版の ops データセットに相当
create schema if not exists ops;

create table if not exists ops.metric_snapshots (
    captured_at   timestamp not null,
    metric        varchar   not null,
    target        varchar   not null,   -- 例: analytics.fct_orders
    value         double    not null
);

create table if not exists ops.monitor_events (
    detected_at   timestamp not null,
    metric        varchar   not null,
    target        varchar   not null,
    value         double,
    baseline      double,
    score         double,
    stage         integer   not null,   -- 0..3, -1 = insufficient_history
    reason        varchar,
    mode          varchar   not null,   -- shadow / active
    last_deploy_sha varchar
);

create table if not exists ops.dbt_run_results (
    invocation_id varchar   not null,
    target        varchar   not null,   -- ci / prod
    git_sha       varchar,
    unique_id     varchar   not null,
    status        varchar   not null,
    execution_seconds double,
    generated_at  timestamp not null
);

create table if not exists ops.deployments (
    deployed_at   timestamp not null,
    git_sha       varchar,
    approver      varchar,
    status        varchar   not null    -- success / failed / rolled_back
);

create table if not exists ops.ci_runs (
    run_at        timestamp not null,
    git_sha       varchar,
    pr_number     varchar,
    attempt       integer   not null,
    status        varchar   not null    -- success / failure
);

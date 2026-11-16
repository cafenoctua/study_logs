-- 週次KPI: 速さ(先行)と安定(遅行)を同じ表で並べる
with weeks as (
    select distinct date_trunc('week', ts) as week from (
        select run_at as ts from ops.ci_runs
        union all select deployed_at from ops.deployments
        union all select detected_at from ops.monitor_events
    )
),
ci as (
    select date_trunc('week', run_at) as week,
           avg(case when attempt = 1 and status = 'success' then 1.0 else 0.0 end)
             filter (where attempt = 1) as ci_first_pass_rate
    from ops.ci_runs group by 1
),
dep as (
    select date_trunc('week', deployed_at) as week,
           avg(case when status in ('failed', 'rolled_back') then 1.0 else 0.0 end) as change_failure_rate,
           count(*) as deployments
    from ops.deployments group by 1
),
mon as (
    select date_trunc('week', detected_at) as week,
           count(*) filter (where stage >= 2 and mode = 'active') as stage2plus_events,
           count(*) filter (where stage >= 2 and mode = 'shadow') as stage2plus_shadow
    from ops.monitor_events group by 1
)
select w.week, ci.ci_first_pass_rate, dep.change_failure_rate, dep.deployments,
       coalesce(mon.stage2plus_events, 0) as stage2plus_events,
       coalesce(mon.stage2plus_shadow, 0) as stage2plus_shadow
from weeks w
left join ci using (week) left join dep using (week) left join mon using (week)
order by w.week desc;

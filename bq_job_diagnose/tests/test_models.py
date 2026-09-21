"""models.py のテスト。

特に以下の境界条件を重点的に検証する:
- Stage.compute_skew_ratio: avg が None / 0 のときに None を返すこと
- Stage.duration_ms: end_ms が None のときに None を返すこと
- Job.has_plan: plan_availability が AVAILABLE 以外なら stages があっても False
- Job.is_script_parent: statement_type による判定
- Stage に比率フィールド（compute_ratio_avg 等）が存在しないこと（設計制約の回帰ガード）
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from bq_job_diagnose.models import (
    Job,
    PlanAvailability,
    Source,
    Stage,
)


def make_stage(
    *,
    id: int = 1,
    name: str = "Stage 1",
    status: str | None = "COMPLETE",
    start_ms: int | None = 0,
    end_ms: int | None = 1000,
    input_stage_ids: tuple[int, ...] = (),
    wait_ms_avg: int | None = None,
    wait_ms_max: int | None = None,
    read_ms_avg: int | None = None,
    read_ms_max: int | None = None,
    compute_ms_avg: int | None = None,
    compute_ms_max: int | None = None,
    write_ms_avg: int | None = None,
    write_ms_max: int | None = None,
    shuffle_output_bytes: int | None = None,
    shuffle_output_bytes_spilled: int | None = None,
    records_read: int | None = None,
    records_written: int | None = None,
    parallel_inputs: int | None = None,
    completed_parallel_inputs: int | None = None,
    slot_ms: int | None = None,
    compute_mode: str | None = None,
    steps: tuple = (),
) -> Stage:
    return Stage(
        id=id,
        name=name,
        status=status,
        start_ms=start_ms,
        end_ms=end_ms,
        input_stage_ids=input_stage_ids,
        wait_ms_avg=wait_ms_avg,
        wait_ms_max=wait_ms_max,
        read_ms_avg=read_ms_avg,
        read_ms_max=read_ms_max,
        compute_ms_avg=compute_ms_avg,
        compute_ms_max=compute_ms_max,
        write_ms_avg=write_ms_avg,
        write_ms_max=write_ms_max,
        shuffle_output_bytes=shuffle_output_bytes,
        shuffle_output_bytes_spilled=shuffle_output_bytes_spilled,
        records_read=records_read,
        records_written=records_written,
        parallel_inputs=parallel_inputs,
        completed_parallel_inputs=completed_parallel_inputs,
        slot_ms=slot_ms,
        compute_mode=compute_mode,
        steps=steps,
    )


def make_job(
    *,
    plan_availability: PlanAvailability = PlanAvailability.AVAILABLE,
    stages: tuple[Stage, ...] = (),
    statement_type: str | None = "SELECT",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> Job:
    return Job(
        source=Source.INFORMATION_SCHEMA,
        job_id="job1",
        project_id="proj",
        location="US",
        parent_job_id=None,
        user_email=None,
        creation_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        start_time=start_time,
        end_time=end_time,
        job_type="QUERY",
        statement_type=statement_type,
        priority=None,
        state="DONE",
        error_result=None,
        query=None,
        cache_hit=None,
        total_bytes_processed=None,
        total_bytes_billed=None,
        total_slot_ms=None,
        referenced_tables=(),
        destination_table=None,
        labels={},
        reservation_id=None,
        edition=None,
        resource_warning=None,
        normalized_literals_hash=None,
        performance_insights=None,
        dml_statistics=None,
        plan_availability=plan_availability,
        stages=stages,
        timeline=(),
    )


class TestStageComputeSkewRatio:
    def test_none_when_avg_is_none(self):
        stage = make_stage(compute_ms_avg=None, compute_ms_max=100)
        assert stage.compute_skew_ratio is None

    def test_none_when_max_is_none(self):
        stage = make_stage(compute_ms_avg=100, compute_ms_max=None)
        assert stage.compute_skew_ratio is None

    def test_none_when_avg_is_zero(self):
        stage = make_stage(compute_ms_avg=0, compute_ms_max=100)
        assert stage.compute_skew_ratio is None

    def test_none_when_avg_is_negative(self):
        stage = make_stage(compute_ms_avg=-1, compute_ms_max=100)
        assert stage.compute_skew_ratio is None

    def test_normal_case(self):
        stage = make_stage(compute_ms_avg=100, compute_ms_max=400)
        assert stage.compute_skew_ratio == pytest.approx(4.0)


class TestStageDurationMs:
    def test_none_when_end_ms_is_none(self):
        stage = make_stage(start_ms=0, end_ms=None)
        assert stage.duration_ms is None

    def test_none_when_start_ms_is_none(self):
        stage = make_stage(start_ms=None, end_ms=100)
        assert stage.duration_ms is None

    def test_normal_case(self):
        stage = make_stage(start_ms=100, end_ms=500)
        assert stage.duration_ms == 400


class TestJobHasPlan:
    def test_true_when_available_and_stages_present(self):
        job = make_job(plan_availability=PlanAvailability.AVAILABLE, stages=(make_stage(),))
        assert job.has_plan is True

    def test_false_when_available_but_no_stages(self):
        job = make_job(plan_availability=PlanAvailability.AVAILABLE, stages=())
        assert job.has_plan is False

    def test_false_when_cache_hit_even_with_stages(self):
        job = make_job(plan_availability=PlanAvailability.CACHE_HIT, stages=(make_stage(),))
        assert job.has_plan is False

    def test_false_when_not_available(self):
        job = make_job(plan_availability=PlanAvailability.NOT_AVAILABLE, stages=(make_stage(),))
        assert job.has_plan is False


class TestJobIsScriptParent:
    def test_true_when_script(self):
        job = make_job(statement_type="SCRIPT")
        assert job.is_script_parent is True

    def test_false_when_select(self):
        job = make_job(statement_type="SELECT")
        assert job.is_script_parent is False

    def test_false_when_none(self):
        job = make_job(statement_type=None)
        assert job.is_script_parent is False


class TestJobElapsedMs:
    def test_none_when_start_time_is_none(self):
        job = make_job(start_time=None, end_time=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert job.elapsed_ms is None

    def test_none_when_end_time_is_none(self):
        job = make_job(start_time=datetime(2026, 1, 1, tzinfo=timezone.utc), end_time=None)
        assert job.elapsed_ms is None

    def test_normal_case(self):
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 0, 0, 1, 500000, tzinfo=timezone.utc)
        job = make_job(start_time=start, end_time=end)
        assert job.elapsed_ms == 1500


class TestStageNoRatioFields:
    """設計制約 #2 の回帰ガード: Stage に比率フィールドを持たせない。"""

    def test_no_ratio_fields_in_slots(self):
        forbidden = {
            "compute_ratio_avg",
            "compute_ratio_max",
            "wait_ratio_avg",
            "wait_ratio_max",
            "read_ratio_avg",
            "read_ratio_max",
            "write_ratio_avg",
            "write_ratio_max",
        }
        assert forbidden.isdisjoint(set(Stage.__slots__))

"""INFORMATION_SCHEMA 経路と SDK(REST) 経路の正規化結果が一致することを検証する。

`tests/fixtures/is_rows/skewed_join.json` と
`tests/fixtures/sdk_jobs/skewed_join.json` は同一の論理ジョブを別の形で
表現したものである。`normalize_row` / `normalize_job` それぞれで正規化した
結果の `Job` が（経路の違いにより構造的に取得できないフィールドを除いて）
一致することを保証するのがこのテストの目的。

比較は `dataclasses.fields()` を使ってフィールドを自動列挙する。
除外フィールドだけを手で列挙する方式にすることで、models.py に
フィールドが増えたときに自動的に比較対象へ含まれるようにする
（除外し忘れれば即座にテストが失敗し、気づける）。
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from bq_job_diagnose import models
from bq_job_diagnose.normalize import from_information_schema as fis
from bq_job_diagnose.normalize import from_sdk

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(subdir: str, name: str) -> dict:
    path = FIXTURES_DIR / subdir / f"{name}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 除外フィールド定義
#
# SDK(REST) 経路では取得できない、または意味が異なるフィールド。
# 増やすときは「なぜ取れないか」を必ず書くこと。
# ---------------------------------------------------------------------------

SDK_UNAVAILABLE_JOB_FIELDS = frozenset(
    {
        "source",  # 経路そのものを表すので当然異なる（INFORMATION_SCHEMA vs JOBS_API）
        "resource_warning",  # INFORMATION_SCHEMA 専用カラム。REST properties には対応する項目がない
        "normalized_literals_hash",  # 同上。REST properties には現れない
        "performance_insights",  # 同上。REST properties の statistics には対応するキーがない
    }
)
SDK_UNAVAILABLE_STAGE_FIELDS = frozenset(set())  # Stage は全フィールドが両経路で取得可能
SDK_UNAVAILABLE_TIMELINE_FIELDS = frozenset(set())  # TimelineSample も同様に全フィールド取得可能


def _job_field_names() -> frozenset[str]:
    return frozenset(f.name for f in dataclasses.fields(models.Job))


def _stage_field_names() -> frozenset[str]:
    return frozenset(f.name for f in dataclasses.fields(models.Stage))


def _timeline_field_names() -> frozenset[str]:
    return frozenset(f.name for f in dataclasses.fields(models.TimelineSample))


def _compare_dataclass(a, b, *, exclude: frozenset[str], label: str) -> list[str]:
    """dataclass 2つをフィールドごとに比較し、不一致フィールド名のリストを返す。"""
    mismatches = []
    for f in dataclasses.fields(a):
        if f.name in exclude:
            continue
        va = getattr(a, f.name)
        vb = getattr(b, f.name)
        if va != vb:
            mismatches.append(f"{label}.{f.name}: is_row={va!r} != sdk={vb!r}")
    return mismatches


# ---------------------------------------------------------------------------
# 除外セットの正当性チェック
# ---------------------------------------------------------------------------


class TestExclusionSetsAreValid:
    """除外セットの中身が実在するフィールド名であることを保証する。

    タイプミスで除外セットが空振りし、比較対象が無自覚に広がることを防ぐ。
    """

    def test_job_exclusions_are_real_fields(self):
        job_fields = _job_field_names()
        for name in SDK_UNAVAILABLE_JOB_FIELDS:
            assert name in job_fields, f"{name!r} は models.Job の実在フィールドではない"

    def test_stage_exclusions_are_real_fields(self):
        stage_fields = _stage_field_names()
        for name in SDK_UNAVAILABLE_STAGE_FIELDS:
            assert name in stage_fields, f"{name!r} は models.Stage の実在フィールドではない"

    def test_timeline_exclusions_are_real_fields(self):
        timeline_fields = _timeline_field_names()
        for name in SDK_UNAVAILABLE_TIMELINE_FIELDS:
            assert name in timeline_fields, (
                f"{name!r} は models.TimelineSample の実在フィールドではない"
            )


# ---------------------------------------------------------------------------
# 本体: skewed_join の parity 比較
# ---------------------------------------------------------------------------


class TestSkewedJoinParity:
    def _normalize_both(self):
        is_row = _load_fixture("is_rows", "skewed_join")
        sdk_props = _load_fixture("sdk_jobs", "skewed_join")
        job_from_is = fis.normalize_row(is_row, location="asia-northeast1")
        job_from_sdk = from_sdk.normalize_job(sdk_props, location="asia-northeast1")
        return job_from_is, job_from_sdk

    def test_job_fields_match_excluding_sdk_unavailable(self):
        job_from_is, job_from_sdk = self._normalize_both()
        mismatches = _compare_dataclass(
            job_from_is,
            job_from_sdk,
            exclude=SDK_UNAVAILABLE_JOB_FIELDS,
            label="Job",
        )
        assert not mismatches, "\n".join(mismatches)

    def test_stage_count_matches(self):
        job_from_is, job_from_sdk = self._normalize_both()
        assert len(job_from_is.stages) == len(job_from_sdk.stages)

    def test_stages_match_pairwise_by_index(self):
        job_from_is, job_from_sdk = self._normalize_both()
        all_mismatches = []
        for i, (stage_is, stage_sdk) in enumerate(
            zip(job_from_is.stages, job_from_sdk.stages, strict=True)
        ):
            mismatches = _compare_dataclass(
                stage_is,
                stage_sdk,
                exclude=SDK_UNAVAILABLE_STAGE_FIELDS,
                label=f"Stage[{i}]",
            )
            all_mismatches.extend(mismatches)
        assert not all_mismatches, "\n".join(all_mismatches)

    def test_timeline_count_matches(self):
        job_from_is, job_from_sdk = self._normalize_both()
        assert len(job_from_is.timeline) == len(job_from_sdk.timeline)

    def test_timeline_samples_match_pairwise_by_index(self):
        job_from_is, job_from_sdk = self._normalize_both()
        all_mismatches = []
        for i, (sample_is, sample_sdk) in enumerate(
            zip(job_from_is.timeline, job_from_sdk.timeline, strict=True)
        ):
            mismatches = _compare_dataclass(
                sample_is,
                sample_sdk,
                exclude=SDK_UNAVAILABLE_TIMELINE_FIELDS,
                label=f"TimelineSample[{i}]",
            )
            all_mismatches.extend(mismatches)
        assert not all_mismatches, "\n".join(all_mismatches)

    def test_steps_match_within_stages(self):
        # Step は除外フィールドの概念を持たないため、そのまま tuple 比較でよい。
        job_from_is, job_from_sdk = self._normalize_both()
        for stage_is, stage_sdk in zip(job_from_is.stages, job_from_sdk.stages, strict=True):
            assert stage_is.steps == stage_sdk.steps

"""config.py のテスト。

TDD: このテストを先に書き、失敗することを確認してから config.py を実装する。
"""

from __future__ import annotations

import re

import pytest
import yaml

from bq_job_diagnose.config import config_digest, load_thresholds


class TestLoadThresholdsDefault:
    def test_default_loads(self):
        th = load_thresholds()
        assert th.version == 1
        assert th.skew.ratio_warning == 4.0
        assert th.skew.ratio_critical == 10.0
        assert th.global_.min_stage_duration_ms == 1000
        assert th.pricing.currency == "USD"
        assert th.scan.default_rank_by == "slot_ms"


class TestPartialOverride:
    def test_override_changes_only_target_key(self, tmp_path):
        override = tmp_path / "override.yaml"
        override.write_text(
            yaml.safe_dump({"version": 1, "skew": {"ratio_warning": 5.0}}),
            encoding="utf-8",
        )
        th = load_thresholds(override)
        assert th.skew.ratio_warning == 5.0
        # 兄弟キーはデフォルトのまま変わらない
        assert th.skew.ratio_critical == 10.0
        assert th.skew.min_compute_ms_max == 5000
        # 他セクションも変わらない
        assert th.global_.min_stage_duration_ms == 1000

    def test_deep_override_nested_dict(self, tmp_path):
        override = tmp_path / "override.yaml"
        override.write_text(
            yaml.safe_dump(
                {"version": 1, "pricing": {"editions_price_per_slot_hour": {"STANDARD": 0.05}}}
            ),
            encoding="utf-8",
        )
        th = load_thresholds(override)
        assert th.pricing.editions_price_per_slot_hour["STANDARD"] == 0.05
        # 兄弟キーは変わらない
        assert th.pricing.editions_price_per_slot_hour["ENTERPRISE"] == 0.06


class TestUnknownKeyRejected:
    def test_unknown_top_level_key_raises(self, tmp_path):
        override = tmp_path / "override.yaml"
        override.write_text(
            yaml.safe_dump({"version": 1, "totally_unknown_section": {"foo": 1}}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="totally_unknown_section"):
            load_thresholds(override)

    def test_unknown_nested_key_raises(self, tmp_path):
        override = tmp_path / "override.yaml"
        override.write_text(
            yaml.safe_dump({"version": 1, "skew": {"totally_unknown_field": 1}}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="skew.totally_unknown_field"):
            load_thresholds(override)


class TestVersionMismatch:
    def test_version_mismatch_raises(self, tmp_path):
        override = tmp_path / "override.yaml"
        override.write_text(
            yaml.safe_dump({"version": 999, "skew": {"ratio_warning": 5.0}}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="version"):
            load_thresholds(override)


class TestConfigDigest:
    def test_stable_for_same_input(self):
        th1 = load_thresholds()
        th2 = load_thresholds()
        assert config_digest(th1) == config_digest(th2)

    def test_differs_when_value_changes(self, tmp_path):
        th_default = load_thresholds()
        override = tmp_path / "override.yaml"
        override.write_text(
            yaml.safe_dump({"version": 1, "skew": {"ratio_warning": 5.0}}),
            encoding="utf-8",
        )
        th_override = load_thresholds(override)
        assert config_digest(th_default) != config_digest(th_override)

    def test_digest_is_12_hex_chars(self):
        th = load_thresholds()
        digest = config_digest(th)
        assert re.fullmatch(r"[0-9a-f]{12}", digest)

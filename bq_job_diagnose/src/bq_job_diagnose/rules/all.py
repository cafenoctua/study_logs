"""全ルールモジュールを import し、`@rule` デコレータによる登録を発火させる。

`rules/__init__.py` はフレームワークのみを提供し、個々のルールモジュールを
import しない設計（変更禁止）。CLI がどのルールを使うか決めるために、
このモジュールを import するだけで全ルールが `default_registry()` に
登録された状態になるようにする。

`report/json_report.py` が同じ目的で個別 import しているのと同じパターン。
"""

from __future__ import annotations

from bq_job_diagnose.rules import cost as _rules_cost
from bq_job_diagnose.rules import filter_efficiency as _rules_filter_efficiency
from bq_job_diagnose.rules import job_status as _rules_job_status
from bq_job_diagnose.rules import joins as _rules_joins
from bq_job_diagnose.rules import plan_shape as _rules_plan_shape
from bq_job_diagnose.rules import skew as _rules_skew
from bq_job_diagnose.rules import slot_starvation as _rules_slot_starvation
from bq_job_diagnose.rules import spill as _rules_spill

# モジュールオブジェクトをこのタプルで「使う」ことで、リンターに
# 未使用importと判定されないようにする（import 自体が副作用＝登録のため）。
ALL_RULE_MODULES = (
    _rules_cost,
    _rules_filter_efficiency,
    _rules_job_status,
    _rules_joins,
    _rules_plan_shape,
    _rules_skew,
    _rules_slot_starvation,
    _rules_spill,
)

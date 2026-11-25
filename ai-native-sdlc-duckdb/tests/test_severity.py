import math

from severity import classify

BASE = [100.0, 101, 99, 100, 102, 98, 100, 101, 99, 100, 100, 101, 99, 100]


def test_insufficient_history():
    v = classify(BASE[:13], 500)
    assert v.stage == -1 and v.reason == "insufficient_history"


def test_normal_value_is_stage0():
    assert classify(BASE, 100.5).stage == 0


def test_stages_increase_with_deviation():
    stages = [classify(BASE, x).stage for x in (100, 102, 103, 105)]
    assert stages == sorted(stages) and stages[-1] == 3


def test_direction_up_ignores_drop():
    assert classify(BASE, 50, direction="up").stage == 0
    assert classify(BASE, 150, direction="up").stage == 3


def test_direction_down_ignores_rise():
    assert classify(BASE, 150, direction="down").stage == 0


def test_constant_history_changed_is_stage3():
    v = classify([10.0] * 14, 11)
    assert v.stage == 3 and math.isinf(v.score)


def test_constant_history_unchanged_is_stage0():
    assert classify([10.0] * 14, 10).stage == 0


def test_robust_survives_single_outlier_where_zscore_misses():
    hist = BASE[:-1] + [10_000.0]  # 履歴に外れ値1件
    assert classify(hist, 110, method="zscore").stage == 0   # σ が膨らみ見逃す
    assert classify(hist, 110, method="robust").stage == 3   # 中央値+MAD なら検知

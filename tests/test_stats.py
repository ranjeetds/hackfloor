import math

import pytest

from hackfloor import stats


def test_sign_test_matches_binomial_tail():
    assert stats.sign_test(5, 0) == pytest.approx(1 / 32)
    assert stats.sign_test(0, 0) == 1.0
    assert stats.sign_test(3, 3) == pytest.approx(sum(math.comb(6, i) for i in range(3, 7)) / 64)


def test_holm_is_monotone_and_bounded():
    adj = stats.holm([0.01, 0.04, 0.03, 0.5])
    assert adj[0] == pytest.approx(0.04)
    assert adj[2] == pytest.approx(0.09)
    assert adj[1] == pytest.approx(0.09)
    assert adj[3] == pytest.approx(0.5)
    assert all(0 <= a <= 1 for a in adj)


def test_clopper_pearson_known_values():
    lo, hi = stats.clopper_pearson(0, 10)
    assert lo == 0.0
    assert hi == pytest.approx(0.3085, abs=1e-3)
    lo, hi = stats.clopper_pearson(5, 10)
    assert lo == pytest.approx(0.1871, abs=1e-3)
    assert hi == pytest.approx(0.8129, abs=1e-3)
    assert stats.clopper_pearson(10, 10)[1] == 1.0


def test_zero_event_upper_is_close_to_rule_of_three():
    assert stats.zero_event_upper(100) == pytest.approx(3 / 100, rel=0.05)


def test_bootstrap_is_seeded_and_brackets_the_mean():
    diffs = [0.0, 0.2, 0.2, 1.0, 0.0, 0.5]
    a = stats.paired_bootstrap_ci(diffs, seed=3)
    b = stats.paired_bootstrap_ci(diffs, seed=3)
    assert a == b
    assert a[0] <= stats.mean(diffs) <= a[1]


def test_point_biserial_and_auroc():
    labels = [True, True, False, False]
    assert stats.point_biserial(labels, [1.0, 1.0, 0.0, 0.0]) == pytest.approx(1.0)
    assert stats.auroc(labels, [1.0, 1.0, 0.0, 0.0]) == 1.0
    assert stats.auroc(labels, [1.0, 1.0, 1.0, 0.0]) == pytest.approx(0.75)
    assert stats.point_biserial(labels, [0.5] * 4) is None
    assert stats.auroc([True, True], [1.0, 0.0]) is None

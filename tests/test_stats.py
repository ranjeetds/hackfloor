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


def _exact_sf(k, n, p):
    """P(X >= k) from exact rational arithmetic, as a float."""
    from fractions import Fraction

    q = Fraction(p).limit_denominator(10**6)
    return float(sum(math.comb(n, i) * q**i * (1 - q) ** (n - i) for i in range(k, n + 1)))


@pytest.mark.parametrize("n", [1, 7, 60, 300, 1000])
@pytest.mark.parametrize("p", [0.5, 0.05, 0.9])
def test_binomial_tails_match_exact_arithmetic(n, p):
    for k in sorted({1, max(1, n // 4), max(1, n // 2), n}):
        exact = _exact_sf(k, n, p)
        assert stats.binom_sf(k, n, p) == pytest.approx(exact, rel=1e-8, abs=1e-300)
        below = 1.0 - _exact_sf(k + 1, n, p) if k < n else 1.0
        assert stats.binom_cdf(k, n, p) == pytest.approx(below, abs=1e-9)


@pytest.mark.parametrize(("k", "n"), [(550, 1100), (1, 2000), (1999, 2000), (100, 5000)])
def test_clopper_pearson_is_finite_for_large_n(k, n):
    # Regression: an exact sum of binomial coefficients raised OverflowError above ~1,030 trials.
    lo, hi = stats.clopper_pearson(k, n)
    assert 0.0 <= lo <= k / n <= hi <= 1.0
    assert hi - lo < 0.2


def test_sign_test_is_finite_for_large_n():
    assert 0.0 < stats.sign_test(1100, 900) < 1e-4
    assert stats.sign_test(1000, 1000) == pytest.approx(0.5, abs=0.03)
    assert stats.sign_test(3000, 10) == pytest.approx(0.0, abs=1e-300)


def test_large_n_statistics_are_fast():
    import time

    start = time.perf_counter()
    for k in (1, 500, 99_999):
        stats.clopper_pearson(k, 100_000)
    stats.sign_test(60_000, 40_000)
    assert time.perf_counter() - start < 2.0


def test_auroc_matches_pairwise_definition_with_ties():
    import random

    rng = random.Random(7)
    for _ in range(100):
        m = rng.randint(2, 40)
        labels = [rng.random() < 0.4 for _ in range(m)]
        values = [rng.choice([0.0, 0.25, 0.5, 1.0]) for _ in range(m)]
        pos = [v for label, v in zip(labels, values, strict=True) if label]
        neg = [v for label, v in zip(labels, values, strict=True) if not label]
        got = stats.auroc(labels, values)
        if not pos or not neg:
            assert got is None
        else:
            want = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))
            assert got == pytest.approx(want, abs=1e-12)


def test_bootstrap_scales_to_large_task_sets():
    import time

    diffs = [1.0 if i % 3 == 0 else 0.0 for i in range(20_000)]
    start = time.perf_counter()
    lo, hi = stats.paired_bootstrap_ci(diffs, seed=1)
    assert lo <= stats.mean(diffs) <= hi
    assert time.perf_counter() - start < 10.0


def test_large_scan_end_to_end_does_not_crash(tmp_path):
    from hackfloor.adapters import RewardFunctionSubject
    from hackfloor.scan import ScanConfig, scan

    def reward(completion, answer):
        return 1.0 if str(answer) in completion else 0.0

    rows = [{"prompt": f"What is {i}+1?", "answer": str(i + 1)} for i in range(1200)]
    result = scan(RewardFunctionSubject(reward, rows), ScanConfig(replays=1))
    assert result.verdict == "VULNERABLE"
    from hackfloor.card import build_card

    assert build_card(result, command="test")["summary"]["tasks"] == 1200

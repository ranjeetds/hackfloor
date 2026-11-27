"""Small, dependency-free statistics used by the scan engine.

All tests are paired per task: a probe and its matched control are graded on the same task,
so task difficulty cancels out.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz's method)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 100_000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """The regularised incomplete beta function I_x(a, b), for a, b > 0.

    It is computed with logarithms and a continued fraction, so it stays finite and fast for
    any number of trials (an exact sum of binomial coefficients overflows a float above
    about 1,000 trials).
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return min(1.0, front * _betacf(a, b, x) / a)
    return max(0.0, 1.0 - front * _betacf(b, a, 1.0 - x) / b)


def binom_sf(k: int, n: int, p: float = 0.5) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    return betainc(k, n - k + 1, p)


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    return betainc(n - k, k + 1, 1.0 - p)


def sign_test(wins: int, losses: int) -> float:
    """Exact one-sided sign test on discordant pairs: P(wins >= observed | no effect)."""
    return binom_sf(wins, wins + losses, 0.5)


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, in the input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [1.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[idx]))
        adjusted[idx] = running
    return adjusted


def _bisect(f, lo: float, hi: float, iters: int = 80) -> float:
    for _ in range(iters):
        mid = (lo + hi) / 2
        if f(mid):
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided (1 - alpha) interval for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    lower = 0.0 if k == 0 else _bisect(lambda p: binom_sf(k, n, p) >= alpha / 2, 0.0, 1.0)
    upper = 1.0 if k == n else _bisect(lambda p: binom_cdf(k, n, p) <= alpha / 2, 0.0, 1.0)
    return (lower, upper)


def zero_event_upper(n: int, alpha: float = 0.05) -> float:
    """One-sided (1 - alpha) upper bound on a rate when 0 of n trials succeeded (~3/n)."""
    if n == 0:
        return 1.0
    return 1.0 - alpha ** (1.0 / n)


#: Up to this many tasks the bootstrap uses the same random stream as in 0.2.1, so published
#: cards reproduce exactly. Above it a faster draw is used (see ``paired_bootstrap_ci``).
BOOTSTRAP_EXACT_STREAM_MAX = 1000
BOOTSTRAP_MAX_DRAWS = 20_000_000
BOOTSTRAP_MIN_REPS = 1000


def paired_bootstrap_ci(
    diffs: Sequence[float], *, reps: int = 2000, alpha: float = 0.05, seed: int = 0
) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean of per-task paired differences."""
    n = len(diffs)
    if n == 0:
        return (0.0, 0.0)
    if n == 1:
        return (diffs[0], diffs[0])
    rng = random.Random(seed)
    if n <= BOOTSTRAP_EXACT_STREAM_MAX:
        means = sorted(sum(rng.choice(diffs) for _ in range(n)) / n for _ in range(reps))
    else:
        # Large task sets: draw whole resamples at once and bound the total work, so the cost
        # grows linearly with n instead of reps * n draws one at a time.
        reps = max(BOOTSTRAP_MIN_REPS, min(reps, BOOTSTRAP_MAX_DRAWS // n))
        means = sorted(sum(rng.choices(diffs, k=n)) / n for _ in range(reps))
    lo = means[math.floor(alpha / 2 * reps)]
    hi = means[min(reps - 1, math.ceil((1 - alpha / 2) * reps) - 1)]
    return (lo, hi)


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def point_biserial(labels: Sequence[bool], values: Sequence[float]) -> float | None:
    """Pearson correlation between a binary label and a value; None if either is constant."""
    n = len(values)
    if n < 2 or len(labels) != n:
        return None
    xs = [1.0 if label else 0.0 for label in labels]
    mx, my = mean(xs), mean(values)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in values)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, values, strict=True))
    return sxy / math.sqrt(sxx * syy)


def auroc(labels: Sequence[bool], values: Sequence[float]) -> float | None:
    """P(a positive outranks a negative), ties counted as one half.

    Computed from ranks (the Mann-Whitney U statistic) in O(m log m) for m samples.
    """
    if len(labels) != len(values):
        raise ValueError("labels and values must have the same length")
    n_pos = sum(1 for label in labels if label)
    n_neg = len(labels) - n_pos
    if not n_pos or not n_neg:
        return None
    order = sorted(range(len(values)), key=values.__getitem__)
    rank_sum = 0.0  # sum of the (average) ranks of the positives, ranks starting at 1
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average_rank = (i + j) / 2 + 1
        rank_sum += average_rank * sum(1 for t in order[i : j + 1] if labels[t])
        i = j + 1
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)

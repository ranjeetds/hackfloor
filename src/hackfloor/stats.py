"""Small, dependency-free statistics used by the scan engine.

All tests are paired per task: a probe and its matched control are graded on the same task,
so task difficulty cancels out.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


def binom_sf(k: int, n: int, p: float = 0.5) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return min(1.0, sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return min(1.0, sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k + 1)))


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
    means = sorted(sum(rng.choice(diffs) for _ in range(n)) / n for _ in range(reps))
    lo = means[math.floor(alpha / 2 * reps)]
    hi = means[min(reps - 1, math.ceil((1 - alpha / 2) * reps) - 1)]
    return (lo, hi)


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0

"""Shared statistical helpers for the Cross-Family Generalization analyses.

Implements:
- ``bootstrap_ci``: percentile bootstrap CI for any rate computed over paired idx.
- ``bootstrap_diff_ci``: paired bootstrap CI for the difference of two rates.
- ``mcnemar_pvalue``: McNemar's test with continuity correction (b, c discordant cells).
- ``pairwise_agreement_rate``: agreement rate for two Series of choices on shared idx.
- ``per_topic_concentration``: top-K share and Gini coefficient over a distribution.

Conventions follow the paper's Appendix A.2 / A.5 and reuse the same seed (42).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import math
import numpy as np
import pandas as pd


BOOTSTRAP_SEED = 42
BOOTSTRAP_RESAMPLES = 2000


@dataclass(frozen=True)
class CI:
    point: float
    low: float
    high: float

    def __iter__(self):
        return iter((self.point, self.low, self.high))


def bootstrap_ci(
    values: np.ndarray,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
    alpha: float = 0.05,
) -> CI:
    """Percentile bootstrap CI for the mean of ``values``.

    ``values`` is a 1-D array of per-item indicators (0/1) or scores; the
    point estimate is the mean. NaNs are dropped.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = arr.size
    if n == 0:
        return CI(float("nan"), float("nan"), float("nan"))
    point = float(arr.mean())
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_resamples, n))
    samples = arr[idx].mean(axis=1)
    low, high = np.quantile(samples, [alpha / 2, 1 - alpha / 2])
    return CI(point, float(low), float(high))


def bootstrap_diff_ci(
    values_a: np.ndarray,
    values_b: np.ndarray,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
    alpha: float = 0.05,
    paired: bool = True,
) -> CI:
    """Bootstrap CI for ``mean(values_a) - mean(values_b)``.

    If ``paired``, the two arrays must be the same length and indices are
    resampled jointly (preserves correlation). Otherwise, they are resampled
    independently.
    """
    a = np.asarray(values_a, dtype=float)
    b = np.asarray(values_b, dtype=float)
    rng = np.random.default_rng(seed)
    if paired:
        mask = ~(np.isnan(a) | np.isnan(b))
        a, b = a[mask], b[mask]
        n = a.size
        if n == 0:
            return CI(float("nan"), float("nan"), float("nan"))
        point = float(a.mean() - b.mean())
        idx = rng.integers(0, n, size=(n_resamples, n))
        samples = a[idx].mean(axis=1) - b[idx].mean(axis=1)
    else:
        a = a[~np.isnan(a)]
        b = b[~np.isnan(b)]
        if a.size == 0 or b.size == 0:
            return CI(float("nan"), float("nan"), float("nan"))
        point = float(a.mean() - b.mean())
        idx_a = rng.integers(0, a.size, size=(n_resamples, a.size))
        idx_b = rng.integers(0, b.size, size=(n_resamples, b.size))
        samples = a[idx_a].mean(axis=1) - b[idx_b].mean(axis=1)
    low, high = np.quantile(samples, [alpha / 2, 1 - alpha / 2])
    return CI(point, float(low), float(high))


def mcnemar_pvalue(b: int, c: int) -> float:
    """McNemar's test with continuity correction on discordant cells (b, c).

    Returns a two-sided p-value. ``b`` is the number of items where
    condition A is positive and B is negative, ``c`` vice versa.
    Uses the chi-square approximation when ``b + c >= 25`` and the exact
    binomial when fewer.
    """
    n = b + c
    if n == 0:
        return 1.0
    if n < 25:
        # Exact two-sided binomial test (Yates correction is degenerate here).
        from math import comb

        k = min(b, c)
        tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
        return float(min(1.0, 2.0 * tail))
    chi = (abs(b - c) - 1.0) ** 2 / n
    # Survival function of chi-square with 1 df at value ``chi``.
    return float(math.erfc(math.sqrt(chi / 2.0)))


def pairwise_agreement_rate(left: pd.Series, right: pd.Series) -> Tuple[float, int]:
    """Return (agreement_rate, n_compared) on the overlap of valid choices."""
    mask = left.notna() & right.notna()
    n = int(mask.sum())
    if n == 0:
        return float("nan"), 0
    agree = int((left[mask].astype(int) == right[mask].astype(int)).sum())
    return agree / n, n


def gini_coefficient(values: Sequence[float]) -> float:
    """Standard Gini coefficient on a non-negative distribution."""
    arr = np.asarray([v for v in values if not np.isnan(v)], dtype=float)
    if arr.size == 0 or arr.sum() == 0:
        return float("nan")
    arr = np.sort(arr)
    n = arr.size
    cum = np.cumsum(arr)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n)


def topk_share(values: Sequence[float], k: int = 3) -> float:
    arr = np.asarray([v for v in values if not np.isnan(v)], dtype=float)
    if arr.size == 0 or arr.sum() == 0:
        return float("nan")
    return float(np.sort(arr)[-k:].sum() / arr.sum())


def binomial_test_two_sided(k: int, n: int, p: float = 0.5) -> float:
    """Exact two-sided binomial test, p-value only."""
    if n == 0:
        return 1.0
    from scipy.stats import binomtest

    return float(binomtest(k, n, p, alternative="two-sided").pvalue)


def cramers_v(table: np.ndarray) -> Tuple[float, float]:
    """Cramer's V (corrected) on a 2-D contingency table, plus chi-square p."""
    from scipy.stats import chi2_contingency

    table = np.asarray(table, dtype=float)
    if table.size == 0 or table.sum() == 0:
        return float("nan"), float("nan")
    chi2, p, _, _ = chi2_contingency(table, correction=False)
    n = table.sum()
    r, c = table.shape
    denom = max(min(r - 1, c - 1), 1)
    v = math.sqrt(max(chi2 / (n * denom), 0.0))
    return float(v), float(p)

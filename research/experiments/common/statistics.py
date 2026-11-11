"""Phân tích thống kê thực nghiệm: Wilson CI, Bootstrap CI và phân tích độ nhạy."""

from __future__ import annotations

import itertools
import math
from statistics import NormalDist
from typing import Any, Callable, Iterable, Sequence

from .config import DEFAULT_SEED
from .imports import np, pd


def _z_score(confidence: float) -> float:
    if not (0.0 < confidence < 1.0):
        raise ValueError("`confidence` phải nằm trong khoảng (0, 1), ví dụ 0.95.")
    return NormalDist().inv_cdf(0.5 + confidence / 2.0)


def wilson_confidence_interval(
    successes: int | float,
    total: int,
    *,
    confidence: float = 0.95,
) -> dict[str, float]:
    """Tính khoảng tin cậy Wilson cho tỷ lệ thắng hoặc tỷ lệ điểm số (`successes / total`)."""
    if total <= 0:
        return {
            "proportion": 0.0,
            "lower": 0.0,
            "upper": 0.0,
            "center": 0.0,
            "margin": 0.0,
            "confidence": confidence,
            "total": 0.0,
        }
    if successes < 0 or successes > total:
        raise ValueError("`successes` phải nằm trong đoạn [0, total].")

    z = _z_score(confidence)
    z2 = z * z
    p = float(successes) / float(total)
    denom = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denom
    margin = (z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * total)) / total)) / denom
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return {
        "proportion": p,
        "lower": lower,
        "upper": upper,
        "center": center,
        "margin": margin,
        "confidence": confidence,
        "total": float(total),
    }


def bootstrap_confidence_interval(
    values: Sequence[float] | Iterable[float],
    *,
    statistic: Callable[[np.ndarray], float] = np.mean,
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = DEFAULT_SEED,
) -> dict[str, float]:
    """Tính khoảng tin cậy phi tham số bằng phương pháp Bootstrap có seed tái lập."""
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return {
            "estimate": 0.0,
            "lower": 0.0,
            "upper": 0.0,
            "std_error": 0.0,
            "confidence": confidence,
            "n_samples": 0.0,
        }
    if not (0.0 < confidence < 1.0):
        raise ValueError("`confidence` phải nằm trong khoảng (0, 1).")
    if n_resamples <= 0:
        raise ValueError("`n_resamples` phải là số nguyên dương.")

    estimate = float(statistic(arr))
    if arr.size == 1:
        return {
            "estimate": estimate,
            "lower": estimate,
            "upper": estimate,
            "std_error": 0.0,
            "confidence": confidence,
            "n_samples": 1.0,
        }

    rng = np.random.default_rng(seed)
    n = arr.size
    boot_stats = np.empty(n_resamples, dtype=float)
    for idx in range(n_resamples):
        sample = rng.choice(arr, size=n, replace=True)
        boot_stats[idx] = float(statistic(sample))

    alpha = (1.0 - confidence) / 2.0
    lower = float(np.quantile(boot_stats, alpha))
    upper = float(np.quantile(boot_stats, 1.0 - alpha))
    return {
        "estimate": estimate,
        "lower": lower,
        "upper": upper,
        "std_error": float(np.std(boot_stats, ddof=1)),
        "confidence": confidence,
        "n_samples": float(n),
    }


def sensitivity_analysis(
    evaluate_fn: Callable[[dict[str, Any]], dict[str, Any]],
    param_grid: dict[str, Sequence[Any]],
) -> pd.DataFrame:
    """Chạy phân tích độ nhạy (grid sweep) theo các tổ hợp siêu tham số và trả về DataFrame."""
    if not param_grid:
        raise ValueError("`param_grid` không được rỗng.")

    keys = list(param_grid.keys())
    value_lists = [list(param_grid[k]) for k in keys]
    rows: list[dict[str, Any]] = []

    for combo in itertools.product(*value_lists):
        params = dict(zip(keys, combo))
        row: dict[str, Any] = dict(params)
        try:
            metrics = evaluate_fn(params)
            if isinstance(metrics, dict):
                row.update(metrics)
            row["error"] = None
        except Exception as exc:
            row["error"] = str(exc)
        rows.append(row)

    return pd.DataFrame(rows)


__all__ = [
    "bootstrap_confidence_interval",
    "sensitivity_analysis",
    "wilson_confidence_interval",
]


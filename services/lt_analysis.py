from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass
class LactatePoint:
    label: str
    load: float
    lactate: float


@dataclass
class SplitFit:
    split_index: int
    slope_left: float
    intercept_left: float
    slope_right: float
    intercept_right: float
    sse: float


@dataclass
class LTResult:
    name: str
    valid: bool
    threshold_load: float | None = None
    split: SplitFit | None = None
    reason: str | None = None
    source_points: list[LactatePoint] | None = None


def _fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def find_best_split(points: Iterable[LactatePoint], min_points_per_side: int = 2) -> SplitFit | None:
    pts = list(points)
    n = len(pts)
    if n < min_points_per_side * 2:
        return None

    x = np.log10(np.array([p.load for p in pts], dtype=float))
    y = np.log10(np.array([p.lactate for p in pts], dtype=float))

    best: SplitFit | None = None
    for split in range(min_points_per_side, n - min_points_per_side + 1):
        left_x, right_x = x[:split], x[split:]
        left_y, right_y = y[:split], y[split:]

        a, b = _fit_line(left_x, left_y)
        c, d = _fit_line(right_x, right_y)

        left_pred = a * left_x + b
        right_pred = c * right_x + d
        sse = float(np.sum((left_y - left_pred) ** 2) + np.sum((right_y - right_pred) ** 2))

        fit = SplitFit(
            split_index=split,
            slope_left=a,
            intercept_left=b,
            slope_right=c,
            intercept_right=d,
            sse=sse,
        )
        if best is None or fit.sse < best.sse:
            best = fit

    return best


def threshold_from_split(points: list[LactatePoint], fit: SplitFit, name: str) -> LTResult:
    denominator = fit.slope_left - fit.slope_right
    if abs(denominator) < 1e-12:
        return LTResult(
            name=name,
            valid=False,
            split=fit,
            reason="두 회귀선의 기울기가 같아 교점을 계산할 수 없습니다.",
            source_points=points,
        )

    log_threshold = (fit.intercept_right - fit.intercept_left) / denominator
    threshold = float(10 ** log_threshold)

    loads = np.array([p.load for p in points], dtype=float)
    if not np.isfinite(threshold) or threshold < loads.min() or threshold > loads.max():
        return LTResult(
            name=name,
            valid=False,
            split=fit,
            reason="계산된 역치가 실제 측정 부하 범위를 벗어났습니다.",
            source_points=points,
        )

    return LTResult(
        name=name,
        valid=True,
        threshold_load=threshold,
        split=fit,
        source_points=points,
    )


def estimate_lt(
    points: Iterable[LactatePoint],
    show_lt1: bool = True,
    show_lt2: bool = True,
) -> tuple[LTResult | None, LTResult | None]:
    valid_points = [
        p
        for p in points
        if p.load is not None
        and p.lactate is not None
        and np.isfinite(p.load)
        and np.isfinite(p.lactate)
        and p.load > 0
        and p.lactate > 0
    ]
    valid_points.sort(key=lambda p: p.load)

    lt1: LTResult | None = None
    lt2: LTResult | None = None

    if show_lt1:
        fit1 = find_best_split(valid_points)
        if fit1 is None:
            lt1 = LTResult(
                name="LT1",
                valid=False,
                reason="LT1 계산에는 유효한 운동 Stage가 최소 4개 필요합니다.",
                source_points=valid_points,
            )
        else:
            lt1 = threshold_from_split(valid_points, fit1, "LT1")

    if show_lt2:
        if not show_lt1 or lt1 is None:
            lt2 = LTResult(name="LT2", valid=False, reason="LT2 계산을 위해 LT1 계산이 필요합니다.")
        elif not lt1.valid or lt1.split is None:
            lt2 = LTResult(name="LT2", valid=False, reason="LT1이 산출되지 않아 LT2를 계산할 수 없습니다.")
        else:
            post_lt1 = valid_points[lt1.split.split_index:]
            fit2 = find_best_split(post_lt1)
            if fit2 is None:
                lt2 = LTResult(
                    name="LT2",
                    valid=False,
                    reason="LT1 후구간에 유효한 운동 Stage가 최소 4개 필요합니다.",
                    source_points=post_lt1,
                )
            else:
                lt2 = threshold_from_split(post_lt1, fit2, "LT2")

    return lt1, lt2

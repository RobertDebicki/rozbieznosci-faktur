"""Proste miary raportu demonstracyjnego."""

from __future__ import annotations

import math


def percentage(correct: int, total: int) -> float | None:
    return round(correct * 100 / total, 2) if total else None


def percentile_ms(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return round(ordered[index], 2)

"""Typy danych potrzebne generatorowi syntetycznych spraw."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseSpec:
    category: str
    baseline_cents: int
    invoice_cents: int
    approved_delta_cents: int
    expected_cause: str

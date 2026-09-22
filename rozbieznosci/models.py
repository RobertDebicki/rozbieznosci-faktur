"""Typy danych potrzebne generatorowi syntetycznych spraw."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Client:
    id: int
    name: str


@dataclass(frozen=True)
class CaseSpec:
    category: str
    baseline_cents: int
    invoice_cents: int
    approved_delta_cents: int
    expected_cause: str


@dataclass(frozen=True)
class Detection:
    invoice_id: int
    client_id: int
    project_id: int
    tranche_id: int | None
    issued_on: date
    invoice_net_cents: int
    invoice_cumulative_cents: int | None
    baseline_cents: int | None
    reference_cents: int | None
    raw_difference_cents: int | None
    adjusted_difference_cents: int | None
    status: str

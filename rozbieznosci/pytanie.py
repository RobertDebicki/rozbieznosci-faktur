"""Bezpieczna, jawna interpretacja prostych pytań o faktury."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .models import Client


@dataclass(frozen=True)
class AnalysisRequest:
    client_id: int | None
    date_from: date
    date_to: date
    min_difference_pct: Decimal = Decimal(0)
    min_difference_cents: int = 0


@dataclass(frozen=True)
class Clarification:
    message: str
    options: tuple[str, ...] = ()


def months_before(day: date, months: int) -> date:
    year, month = divmod(day.year * 12 + day.month - 1 - months, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def parse_request(text: str, today: date, clients: list[Client]) -> AnalysisRequest | Clarification:
    """Zrozum typowe sformułowania; przy niepewności poproś o doprecyzowanie."""
    question = " ".join(text.strip().split())
    lower = question.casefold()
    if question and not any(word in lower for word in ("faktur", "rozbież", "rozbiezn", "wycen", "różnic")):
        return Clarification("Mogę sprawdzić rozbieżności faktur i wycen. Sprecyzuj pytanie o faktury.")

    client_id: int | None = None
    match = re.search(
        r"\bklienta?\s+(.+?)(?=\s+(?:z ostatniego|z ostatnich|od \d{4}|za okres|powyżej|minimum)|$)",
        question, flags=re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip().casefold()
        candidates = [client for client in clients if name in client.name.casefold()]
        if len(candidates) != 1:
            return Clarification(
                "Wybierz dokładnego klienta." if candidates else "Nie znalazłem takiego klienta.",
                tuple(client.name for client in candidates),
            )
        client_id = candidates[0].id

    explicit = re.search(r"\bod\s+(\d{4}-\d{2}-\d{2})\s+do\s+(\d{4}-\d{2}-\d{2})", lower)
    if explicit:
        try:
            date_from, date_to = date.fromisoformat(explicit.group(1)), date.fromisoformat(explicit.group(2))
        except ValueError:
            return Clarification("Podaj poprawne daty w formacie RRRR-MM-DD.")
    else:
        months = 6 if "pół roku" in lower or "pol roku" in lower else 12
        if "ostatni miesiąc" in lower or "ostatniego miesiąca" in lower:
            months = 1
        date_from, date_to = months_before(today, months), today
    if date_from > date_to:
        return Clarification("Data początkowa jest późniejsza od końcowej.")

    threshold = re.search(r"(?:powyżej|minimum|co najmniej)\s+(\d+(?:[,.]\d+)?)\s*%", lower)
    min_pct = Decimal(threshold.group(1).replace(",", ".")) if threshold else Decimal(0)
    return AnalysisRequest(client_id, date_from, date_to, min_pct)

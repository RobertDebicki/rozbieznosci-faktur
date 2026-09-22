"""Proste pytania księgowych zamieniane na jawne filtry."""

from datetime import date
from decimal import Decimal

from rozbieznosci.models import Client
from rozbieznosci.pytanie import AnalysisRequest, Clarification, parse_request


CLIENTS = [Client(1, "Firma Demo 01 Sp. z o.o."), Client(2, "Firma Demo 02 Sp. z o.o.")]


def test_last_six_months_and_client() -> None:
    result = parse_request(
        "Sprawdź rozbieżności na fakturach klienta Firma Demo 01 z ostatniego pół roku",
        date(2026, 9, 22), CLIENTS,
    )
    assert isinstance(result, AnalysisRequest)
    assert result.client_id == 1
    assert result.date_from == date(2026, 3, 22)
    assert result.date_to == date(2026, 9, 22)


def test_explicit_dates_and_percentage_threshold() -> None:
    result = parse_request(
        "Pokaż rozbieżności od 2026-01-01 do 2026-06-30 powyżej 10%",
        date(2026, 9, 22), CLIENTS,
    )
    assert isinstance(result, AnalysisRequest)
    assert (result.date_from, result.date_to) == (date(2026, 1, 1), date(2026, 6, 30))
    assert result.min_difference_pct == Decimal("10")


def test_ambiguous_and_unknown_client_ask_for_clarification() -> None:
    ambiguous = parse_request("Faktury klienta Firma Demo", date(2026, 9, 22), CLIENTS)
    assert isinstance(ambiguous, Clarification)
    assert len(ambiguous.options) == 2
    unknown = parse_request("Faktury klienta Nieznana Firma", date(2026, 9, 22), CLIENTS)
    assert isinstance(unknown, Clarification)


def test_invalid_period_and_out_of_scope_question() -> None:
    reversed_dates = parse_request(
        "Faktury od 2026-12-01 do 2026-01-01", date(2026, 9, 22), CLIENTS
    )
    assert isinstance(reversed_dates, Clarification)
    unrelated = parse_request("Ile wynosi podatek dochodowy?", date(2026, 9, 22), CLIENTS)
    assert isinstance(unrelated, Clarification)

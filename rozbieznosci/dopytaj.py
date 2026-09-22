"""Bezpieczne odpowiedzi uzupełniające ze stanu zapisanej analizy."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass

from .model import LLMProvider
from .wyjasnij import _pln


@dataclass(frozen=True)
class FollowupAnswer:
    status: str
    text: str
    case_id: int | None = None
    source_ids: tuple[int, ...] = ()


def answer_followup(
    analysis_id: int,
    case_id: int | None,
    question: str,
    db: sqlite3.Connection,
    provider: LLMProvider,
) -> FollowupAnswer:
    """Odpowiedz z zamrożonego wyniku; nie pobieraj obcych projektów ani kwot."""
    row = db.execute("SELECT result_json FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if row is None:
        raise ValueError("Nie znaleziono analizy.")
    analysis = json.loads(row[0])
    cases = analysis["cases"]
    words = " ".join(question.strip().casefold().split())
    if not words:
        return FollowupAnswer("cannot_answer", "Napisz pytanie o tę analizę lub jedną z jej faktur.")
    if ("sprawdź klienta" in words or "sprawdz klienta" in words
            or "innego klienta" in words or "poprzedniego roku" in words
            or "nowy okres" in words):
        return FollowupAnswer(
            "new_analysis_required",
            "To zmienia zakres danych. Uruchom nową analizę i wybierz właściwego klienta lub okres.",
        )

    if "największ" in words or "najwieksz" in words:
        differences = [item for item in cases if item["status"] == "difference"]
        if not differences:
            return FollowupAnswer("answered", "W tej analizie nie ma rozbieżności.")
        biggest = max(differences, key=lambda item: abs(item["difference_cents"]))
        return FollowupAnswer(
            "answered",
            f"Największa różnica to {_pln(biggest['difference_cents'])} na fakturze "
            f"{biggest['invoice_number']} (projekt DEMO-{biggest['project_id']:03d}).",
            biggest["invoice_id"],
        )

    invoice_number = re.search(r"fv/\d{4}/\d{3}", words)
    if invoice_number:
        matched = next((item for item in cases if item["invoice_number"].casefold() == invoice_number.group()), None)
        if matched is None:
            return FollowupAnswer("cannot_answer", "Tej faktury nie ma w bieżącej analizie.")
        case_id = matched["invoice_id"]
    case = next((item for item in cases if item["invoice_id"] == case_id), None) if case_id is not None else None
    if case_id is not None and case is None:
        return FollowupAnswer("cannot_answer", "Tej sprawy nie ma w bieżącej analizie.")

    if case and any(word in words for word in ("dlaczego", "przyczyn", "czemu", "skąd", "skad", "dowód", "dowod", "rabat", "zmian", "źródł", "zrodl")):
        explanation = case["explanation"]
        if explanation["cause"] == "unknown" or not explanation["evidence_ids"]:
            return FollowupAnswer(
                "answered", f"Dla faktury {case['invoice_number']} przyczyna pozostaje nieustalona. "
                "W dostępnych źródłach nie ma potwierdzenia.", case["invoice_id"],
            )
        return FollowupAnswer(
            "answered",
            f"Dla faktury {case['invoice_number']}: {explanation['text']} "
            f"Cytat: „{explanation['quotes'][0]}”",
            case["invoice_id"], tuple(explanation["evidence_ids"]),
        )

    if case and any(word in words for word in ("ile", "kwot", "różnic", "roznic")):
        return FollowupAnswer(
            "answered", f"Różnica na fakturze {case['invoice_number']} wynosi "
            f"{_pln(case['difference_cents'])} netto.", case["invoice_id"],
        )
    if any(word in words for word in ("ile", "liczb", "wiele")) and "rozbież" in words:
        count = sum(item["status"] == "difference" for item in cases)
        return FollowupAnswer("answered", f"W tej analizie znaleziono {count} rozbieżności.")

    return FollowupAnswer(
        "cannot_answer",
        "Mogę wskazać największą różnicę, policzyć rozbieżności albo wyjaśnić "
        "konkretną fakturę na podstawie zapisanych źródeł. Zadaj jedno z takich pytań.",
    )

"""Deterministyczne wykrywanie różnic, bez udziału modelu językowego."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from .models import Detection


def detect(
    db: sqlite3.Connection,
    client_id: int | None,
    date_from: date,
    date_to: date,
    min_difference_cents: int = 0,
    min_difference_pct: Decimal = Decimal(0),
) -> list[Detection]:
    """Porównaj faktury w okresie z transzą i zatwierdzoną kwotą referencyjną.

    Różnica jest liczona względem pierwotnej wyceny transzy. Kwota po
    zatwierdzonych zmianach jest dostępna osobno, aby wyjaśniacz mógł
    rozróżnić udokumentowaną zmianę od błędu.
    """
    if date_from > date_to:
        raise ValueError("Data początkowa nie może być późniejsza od końcowej.")
    if min_difference_cents < 0 or min_difference_pct < 0:
        raise ValueError("Progi rozbieżności nie mogą być ujemne.")

    rows = db.execute(
        "SELECT i.id, i.client_id, i.project_id, i.tranche_id, i.issued_on, "
        "i.net_cents, t.baseline_cents, t.status, r.reference_cents "
        "FROM invoices i "
        "LEFT JOIN tranches t ON t.id = i.tranche_id "
        "LEFT JOIN tranche_references r ON r.tranche_id = i.tranche_id "
        "WHERE i.issued_on >= ? AND i.issued_on <= ? "
        "AND (? IS NULL OR i.client_id = ?) "
        "ORDER BY i.issued_on, i.id",
        (date_from.isoformat(), date_to.isoformat(), client_id, client_id),
    ).fetchall()

    results: list[Detection] = []
    for invoice_id, row_client_id, project_id, tranche_id, issued_on, net_cents, baseline, tranche_status, reference in rows:
        invoice_date = date.fromisoformat(issued_on)
        if tranche_id is None or baseline is None or reference is None:
            if min_difference_cents or min_difference_pct:
                continue
            results.append(Detection(
                invoice_id, row_client_id, project_id, tranche_id, invoice_date,
                net_cents, None, None, None, None, None, "not_comparable",
            ))
            continue

        cumulative = db.execute(
            "SELECT COALESCE(SUM(net_cents), 0) FROM invoices "
            "WHERE tranche_id = ? AND (issued_on < ? OR (issued_on = ? AND id <= ?))",
            (tranche_id, issued_on, issued_on, invoice_id),
        ).fetchone()[0]
        raw_difference = cumulative - baseline
        adjusted_difference = cumulative - reference

        if raw_difference > 0 or adjusted_difference > 0:
            status = "difference"
        elif raw_difference < 0 and (
            tranche_status == "paid"
            or (reference < baseline and cumulative == reference)
        ):
            status = "difference"
        else:
            status = "equal"

        amount_for_threshold = abs(raw_difference or adjusted_difference)
        if min_difference_cents or min_difference_pct:
            if status != "difference" or amount_for_threshold < min_difference_cents:
                continue
            if min_difference_pct:
                if baseline == 0:
                    continue
                percentage = Decimal(amount_for_threshold) * 100 / Decimal(baseline)
                if percentage < min_difference_pct:
                    continue

        results.append(Detection(
            invoice_id, row_client_id, project_id, tranche_id, invoice_date,
            net_cents, cumulative, baseline, reference,
            raw_difference, adjusted_difference, status,
        ))
    return results

"""Pokaż deterministycznie policzone sprawy z syntetycznej bazy."""

from __future__ import annotations

import argparse
import calendar
from datetime import date
from decimal import Decimal
from pathlib import Path

from rozbieznosci.db import open_db
from rozbieznosci.detektor import detect


def _months_before(day: date, months: int) -> date:
    year, month = divmod(day.year * 12 + day.month - 1 - months, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _pln(cents: int | None) -> str:
    if cents is None:
        return "—"
    sign = "−" if cents < 0 else "+" if cents > 0 else ""
    amount = abs(cents)
    return f"{sign}{amount // 100},{amount % 100:02d} zł"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("dane/demo.sqlite"))
    parser.add_argument("--client-id", type=int)
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat)
    parser.add_argument("--to", dest="date_to", type=date.fromisoformat)
    parser.add_argument("--last-months", type=int, default=12)
    parser.add_argument("--min-pln", type=Decimal, default=Decimal(0))
    parser.add_argument("--min-percent", type=Decimal, default=Decimal(0))
    args = parser.parse_args()

    if not args.db.is_file():
        parser.error(f"Brak bazy {args.db}. Najpierw uruchom skrypty.generuj_dane.")
    if args.last_months < 0 or args.min_pln < 0 or args.min_percent < 0:
        parser.error("Okres i progi nie mogą być ujemne.")

    today = date.today()
    date_from = args.date_from or _months_before(today, args.last_months)
    date_to = args.date_to or today
    cents = args.min_pln * 100
    if cents != cents.to_integral_value():
        parser.error("Próg w złotych może mieć najwyżej dwa miejsca po przecinku.")

    db = open_db(args.db)
    try:
        cases = detect(
            db, args.client_id, date_from, date_to,
            min_difference_cents=int(cents),
            min_difference_pct=args.min_percent,
        )
        for case in cases:
            number = db.execute(
                "SELECT number FROM invoices WHERE id = ?", (case.invoice_id,)
            ).fetchone()[0]
            print(f"{number} | {case.status} | {_pln(case.raw_difference_cents)}")
    finally:
        db.close()
    print(f"Sprawdzone faktury: {len(cases)}")
    print(f"Rozbieżności: {sum(case.status == 'difference' for case in cases)}")
    print(f"Nieporównywalne: {sum(case.status == 'not_comparable' for case in cases)}")


if __name__ == "__main__":
    main()

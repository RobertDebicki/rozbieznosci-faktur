"""Deterministyczne porównanie faktur z właściwymi transzami."""

from datetime import date
from decimal import Decimal
from pathlib import Path
import subprocess
import sys

import pytest

from rozbieznosci.db import open_db, seed_demo
from rozbieznosci.detektor import detect


@pytest.fixture
def demo_db(tmp_path: Path):
    db = open_db(tmp_path / "demo.sqlite")
    seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
    yield db
    db.close()


def test_approved_change_and_discount_keep_original_difference_visible(demo_db) -> None:
    """Zatwierdzona zmiana wyjaśnia różnicę, ale nie usuwa jej z listy."""
    cases = {
        item.invoice_id: item
        for item in detect(demo_db, None, date(2025, 1, 1), date(2027, 1, 1))
    }
    assert len(cases) == 30
    assert sum(item.status == "equal" for item in cases.values()) == 5
    assert sum(item.status == "difference" for item in cases.values()) == 25
    assert cases[1].status == "equal"
    assert cases[1].baseline_cents == 1_100_000
    assert cases[1].invoice_cumulative_cents == 1_100_000
    assert cases[2].raw_difference_cents == 240_000
    assert cases[2].adjusted_difference_cents == 0
    assert cases[2].status == "difference"
    assert cases[3].raw_difference_cents == -150_000
    assert cases[3].adjusted_difference_cents == 0
    assert cases[3].status == "difference"
    assert cases[5].adjusted_difference_cents == 230_000


def test_client_and_date_filter_include_boundaries(demo_db) -> None:
    """Zapytanie o klienta i konkretny dzień nie zwraca innych faktur."""
    invoice_date = date.fromisoformat(
        demo_db.execute("SELECT issued_on FROM invoices WHERE id = 1").fetchone()[0]
    )
    cases = detect(demo_db, client_id=1, date_from=invoice_date, date_to=invoice_date)
    assert [item.invoice_id for item in cases] == [1]


def test_partial_invoice_uses_earlier_payment_outside_filter(demo_db) -> None:
    """Częściowa faktura nie jest alarmem, a suma obejmuje wcześniejsze wpłaty."""
    baseline = demo_db.execute(
        "SELECT baseline_cents FROM tranches WHERE id = "
        "(SELECT tranche_id FROM invoices WHERE id = 1)"
    ).fetchone()[0]
    demo_db.execute(
        "UPDATE invoices SET issued_on = '2026-01-01', net_cents = ? WHERE id = 1",
        (baseline // 2,),
    )
    demo_db.execute(
        "INSERT INTO invoices "
        "(id, client_id, project_id, tranche_id, issued_on, number, net_cents, vat_cents) "
        "SELECT 31, client_id, project_id, tranche_id, '2026-06-01', "
        "'FV/2026/031', ?, ? FROM invoices WHERE id = 1",
        (baseline // 2, baseline * 23 // 200),
    )
    cases = detect(demo_db, 1, date(2026, 6, 1), date(2026, 6, 1))
    assert [item.invoice_id for item in cases] == [31]
    assert cases[0].invoice_cumulative_cents == baseline
    assert cases[0].status == "equal"


def test_unknown_tranche_is_not_guessed(demo_db) -> None:
    """Faktura bez przypisanej transzy ma status braku porównania."""
    demo_db.execute(
        "INSERT INTO invoices "
        "(id, client_id, project_id, tranche_id, issued_on, number, net_cents, vat_cents) "
        "VALUES (31, 1, 1, NULL, '2026-06-01', 'FV/2026/031', 10000, 2300)"
    )
    cases = detect(demo_db, 1, date(2026, 6, 1), date(2026, 6, 1))
    assert [item.invoice_id for item in cases] == [31]
    assert cases[0].status == "not_comparable"
    assert cases[0].raw_difference_cents is None


def test_vat_and_payment_retention_do_not_change_net_difference(demo_db) -> None:
    """VAT i kaucja płatnicza nie są dopłatą do wyceny netto."""
    demo_db.execute(
        "UPDATE invoices SET vat_cents = 999999, retention_cents = 120000 WHERE id = 1"
    )
    invoice_date = date.fromisoformat(
        demo_db.execute("SELECT issued_on FROM invoices WHERE id = 1").fetchone()[0]
    )
    case = detect(demo_db, 1, invoice_date, invoice_date)[0]
    assert case.status == "equal"
    assert case.raw_difference_cents == 0


def test_thresholds_and_invalid_range(demo_db) -> None:
    """Próg działa na różnicy brutto z wyceny, a błędne daty są odrzucane."""
    cases = detect(
        demo_db, None, date(2025, 1, 1), date(2027, 1, 1),
        min_difference_cents=230_000, min_difference_pct=Decimal("10"),
    )
    ids = {item.invoice_id for item in cases}
    assert 2 in ids  # 240 000 / 2 080 000 = 11,54%
    assert 3 not in ids  # 150 000 / 1 060 000 = 14,15%, ale poniżej progu kwoty
    assert 1 not in ids  # brak różnicy
    with pytest.raises(ValueError):
        detect(demo_db, None, date(2026, 9, 23), date(2026, 9, 22))


def test_cli_prints_detected_cases(demo_db) -> None:
    """Detektor można uruchomić i sprawdzić bez interfejsu webowego."""
    db_path = demo_db.execute("PRAGMA database_list").fetchone()[2]
    result = subprocess.run(
        [sys.executable, "-m", "skrypty.sprawdz", "--db", db_path,
         "--from", "2025-01-01", "--to", "2027-01-01"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "FV/2026/002" in result.stdout
    assert "Rozbieżności: 25" in result.stdout

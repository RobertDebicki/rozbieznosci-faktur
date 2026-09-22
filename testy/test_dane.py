"""Kontrakty syntetycznej bazy przed implementacją generatora."""

import json
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from rozbieznosci.db import open_db, seed_demo


def test_generator_is_repeatable_and_creates_30_cases(tmp_path: Path) -> None:
    """Inne uruchomienie z tym samym ziarnem nie może zmieniać faktur."""
    snapshots = []
    for name in ("first", "second"):
        corpus = tmp_path / name
        with open_db(tmp_path / f"{name}.sqlite") as db:
            seed_demo(db, seed=2026, corpus_dir=corpus)
            snapshots.append(
                db.execute(
                    "SELECT client_id, project_id, tranche_id, issued_on, net_cents "
                    "FROM invoices ORDER BY id"
                ).fetchall()
            )
            assert db.execute("SELECT count(*) FROM invoices").fetchone()[0] == 30
            assert db.execute("SELECT count(*) FROM projects").fetchone()[0] == 30
            assert db.execute("SELECT count(*) FROM documents").fetchone()[0] >= 30
            assert all(Path(row[0]).is_file() for row in db.execute("SELECT path FROM documents"))
    assert snapshots[0] == snapshots[1]


def test_database_rejects_broken_relations_and_fractional_money(tmp_path: Path) -> None:
    """Błędny projekt lub kwota ułamkowa nie mogą wejść do faktur."""
    with open_db(tmp_path / "demo.sqlite") as db:
        seed_demo(db, corpus_dir=tmp_path / "docs")
        valid = db.execute(
            "SELECT id, client_id, project_id, tranche_id, issued_on, number, net_cents, vat_cents "
            "FROM invoices LIMIT 1"
        ).fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO invoices (client_id, project_id, tranche_id, issued_on, number, net_cents, vat_cents) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (valid[1], 99999, valid[3], valid[4], "FV/INVALID", 10000, 2300),
            )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO invoices (client_id, project_id, tranche_id, issued_on, number, net_cents, vat_cents) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (valid[1], valid[2], valid[3], valid[4], "FV/FRACTION", 10000.5, 2300),
            )


def test_invoice_must_use_its_projects_client_and_tranche(tmp_path: Path) -> None:
    """Istniejące ID z innej sprawy nie mogą zostać połączone w jedną fakturę."""
    with open_db(tmp_path / "demo.sqlite") as db:
        seed_demo(db, corpus_dir=tmp_path / "docs")
        invoice = db.execute(
            "SELECT client_id, project_id, tranche_id, issued_on FROM invoices WHERE id = 1"
        ).fetchone()
        other_client = db.execute("SELECT client_id FROM projects WHERE id = 2").fetchone()[0]
        other_tranche = db.execute("SELECT id FROM tranches WHERE stage_id = 2 LIMIT 1").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO invoices (client_id, project_id, tranche_id, issued_on, number, net_cents, vat_cents) "
                "VALUES (?, ?, ?, ?, ?, 10000, 2300)",
                (other_client, invoice[1], invoice[2], invoice[3], "FV/WRONG-CLIENT"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO invoices (client_id, project_id, tranche_id, issued_on, number, net_cents, vat_cents) "
                "VALUES (?, ?, ?, ?, ?, 10000, 2300)",
                (invoice[0], invoice[1], other_tranche, invoice[3], "FV/WRONG-TRANCHE"),
            )


def test_reference_amount_ignores_unapproved_changes(tmp_path: Path) -> None:
    """Wycena transzy zmienia się tylko po zatwierdzeniu aneksu."""
    with open_db(tmp_path / "demo.sqlite") as db:
        seed_demo(db, corpus_dir=tmp_path / "docs")
        tranche_id = db.execute(
            "SELECT tranche_id FROM invoices WHERE id = 2"
        ).fetchone()[0]
        baseline = db.execute(
            "SELECT baseline_cents FROM tranches WHERE id = ?", (tranche_id,)
        ).fetchone()[0]
        approved = db.execute(
            "SELECT delta_cents FROM changes WHERE tranche_id = ? AND approved = 1",
            (tranche_id,),
        ).fetchone()[0]
        before = db.execute(
            "SELECT reference_cents FROM tranche_references WHERE tranche_id = ?",
            (tranche_id,),
        ).fetchone()[0]
        assert before == baseline + approved
        db.execute(
            "INSERT INTO changes (stage_id, tranche_id, kind, delta_cents, approved) "
            "VALUES (2, ?, 'scope', 999999, 0)",
            (tranche_id,),
        )
        after = db.execute(
            "SELECT reference_cents FROM tranche_references WHERE tranche_id = ?",
            (tranche_id,),
        ).fetchone()[0]
        assert after == before


def test_generated_invoice_dates_follow_demo_date(tmp_path: Path) -> None:
    """Demo uruchomione później nadal musi mieć faktury z ostatniego roku."""
    with open_db(tmp_path / "demo.sqlite") as db:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2027, 3, 1))
        dates = [date.fromisoformat(row[0]) for row in db.execute("SELECT issued_on FROM invoices")]
        assert max(dates) <= date(2027, 3, 1)
        assert min(dates) >= date(2026, 3, 1)
        assert len({day.month for day in dates}) >= 6


def test_invoice_number_uses_its_issue_year(tmp_path: Path) -> None:
    """Po zmianie roku numer faktury nie może nadal wskazywać 2026."""
    with open_db(tmp_path / "demo.sqlite") as db:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2027, 3, 1))
        rows = db.execute("SELECT number, issued_on FROM invoices").fetchall()
        assert {issued_on[:4] for _, issued_on in rows} == {"2026", "2027"}
        assert all(number.split("/")[1] == issued_on[:4] for number, issued_on in rows)


def test_cli_writes_evaluation_set_with_unknown_cases(tmp_path: Path) -> None:
    """Ewaluacja musi mieć 30 etykiet, w tym 5 spraw bez dowodu."""
    db_path = tmp_path / "demo.sqlite"
    corpus = tmp_path / "docs"
    evaluation = tmp_path / "zestaw.jsonl"
    result = subprocess.run(
        [
            sys.executable, "-m", "skrypty.generuj_dane",
            "--db", str(db_path), "--corpus", str(corpus),
            "--evaluation", str(evaluation), "--seed", "2026",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    rows = [json.loads(line) for line in evaluation.read_text().splitlines()]
    assert len(rows) == 30
    assert len({row["invoice_id"] for row in rows}) == 30
    assert sum(row["expected_cause"] == "unknown" for row in rows) == 5
    assert {row["expected_cause"] for row in rows} == {
        "none", "approved_change", "discount", "extra_work", "invoice_or_estimate_error", "unknown"
    }

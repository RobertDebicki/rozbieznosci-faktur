"""Schemat SQLite i odtwarzalne syntetyczne dane demonstracyjne."""

from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from .models import CaseSpec


SCHEMA = Path(__file__).with_name("schema.sql")
CATEGORIES = (
    "staged_billing", "approved_change", "discount", "extra_work",
    "invoice_or_estimate_error", "unknown",
)


def open_db(path: Path) -> sqlite3.Connection:
    """Otwórz bazę z włączonymi kluczami obcymi i gotowym schematem."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA.read_text(encoding="utf-8"))
    return db


def _case_spec(category: str, baseline: int, rng: random.Random) -> CaseSpec:
    delta = rng.randint(8, 24) * 10_000
    if category == "staged_billing":
        return CaseSpec(category, baseline, baseline, 0, "none")
    if category == "approved_change":
        return CaseSpec(category, baseline, baseline + delta, delta, category)
    if category == "discount":
        return CaseSpec(category, baseline, baseline - delta, -delta, category)
    if category == "extra_work":
        return CaseSpec(category, baseline, baseline + delta, delta, category)
    return CaseSpec(category, baseline, baseline + delta, 0, category)


def seed_demo(
    db: sqlite3.Connection,
    seed: int = 2026,
    corpus_dir: Path | None = None,
    as_of: date | None = None,
) -> list[dict[str, object]]:
    """Wypełnij pustą bazę 30 sprawami i zwróć etykiety ewaluacyjne."""
    if db.execute("SELECT 1 FROM clients LIMIT 1").fetchone():
        raise ValueError("Baza zawiera już dane. Wybierz nową ścieżkę bazy.")

    rng = random.Random(seed)
    anchor = as_of or date.today()
    corpus = Path(corpus_dir) if corpus_dir else Path("dane/syntetyczne")
    corpus.mkdir(parents=True, exist_ok=True)
    labels: list[dict[str, object]] = []

    for client_id in range(1, 11):
        db.execute(
            "INSERT INTO clients (id, name, tax_id) VALUES (?, ?, ?)",
            (client_id, f"Firma Demo {client_id:02d} Sp. z o.o.", f"900000{client_id:04d}"),
        )

    for index in range(30):
        case_id = index + 1
        client_id = index % 10 + 1
        category = CATEGORIES[index % len(CATEGORIES)]
        baseline = rng.randint(80, 240) * 10_000
        spec = _case_spec(category, baseline, rng)
        full_project_cents = baseline * 2
        project_code = f"DEMO-{case_id:03d}"
        first_tranche_id = case_id * 2 - 1
        second_tranche_id = case_id * 2
        issue_date = (
            anchor - timedelta(days=7 + (index % 8) * 30 + (index // 8) * 3)
        ).isoformat()

        db.execute(
            "INSERT INTO projects (id, client_id, name, code) VALUES (?, ?, ?, ?)",
            (case_id, client_id, f"Projekt demonstracyjny {case_id:02d}", project_code),
        )
        db.execute(
            "INSERT INTO estimates (project_id, version, approved, net_cents) VALUES (?, 1, 1, ?)",
            (case_id, full_project_cents),
        )
        db.execute(
            "INSERT INTO stages (id, project_id, name, baseline_cents, status) "
            "VALUES (?, ?, ?, ?, 'open')",
            (case_id, case_id, "Etap I", full_project_cents),
        )
        db.execute(
            "INSERT INTO tranches (id, stage_id, sequence, baseline_cents, acceptance_condition, status) "
            "VALUES (?, ?, 1, ?, ?, 'due')",
            (first_tranche_id, case_id, baseline, "Protokół odbioru pierwszej transzy"),
        )
        db.execute(
            "INSERT INTO tranches (id, stage_id, sequence, baseline_cents, acceptance_condition, status) "
            "VALUES (?, ?, 2, ?, ?, 'planned')",
            (second_tranche_id, case_id, baseline, "Zamknięcie etapu"),
        )

        document_index = 0

        def add_document(kind: str, title: str, body: str, available: bool = True) -> int:
            nonlocal document_index
            document_index += 1
            filename = f"{project_code}-{kind}-{document_index}.txt"
            path = corpus / filename
            if path.exists():
                if path.read_text(encoding="utf-8") != body:
                    raise ValueError("Dokument już istnieje z inną treścią. Wybierz inny katalog korpusu.")
            else:
                path.write_text(body, encoding="utf-8")
            cursor = db.execute(
                "INSERT INTO documents (project_id, kind, title, path, available) "
                "VALUES (?, ?, ?, ?, ?)",
                (case_id, kind, title, str(path.resolve()), int(available)),
            )
            return int(cursor.lastrowid)

        estimate_doc = add_document(
            "estimate", f"Wycena {project_code}",
            f"Wycena {project_code}. Kwota całego projektu netto: {full_project_cents} groszy. "
            f"Pierwsza transza netto: {baseline} groszy. Druga transza: {baseline} groszy.",
        )
        add_document(
            "contract", f"Umowa {project_code}",
            f"Umowa {project_code}. Projekt rozliczany w dwóch transzach. "
            "Pierwsza transza po odbiorze części prac, druga po zamknięciu etapu.",
        )

        evidence_ids: list[int] = [estimate_doc]
        if category in {"approved_change", "discount", "extra_work"}:
            if category == "approved_change":
                kind, change_kind = "amendment", "scope"
                title = f"Aneks nr 1 do {project_code}"
                body = f"Zatwierdzono zmianę zakresu pierwszej transzy o {spec.approved_delta_cents} groszy netto."
            elif category == "discount":
                kind, change_kind = "email", "discount"
                title = f"Potwierdzenie rabatu {project_code}"
                body = f"Klient i wykonawca zatwierdzili rabat {abs(spec.approved_delta_cents)} groszy netto dla pierwszej transzy."
            else:
                kind, change_kind = "acceptance", "extra_work"
                title = f"Protokół prac dodatkowych {project_code}"
                body = f"Odebrano dodatkowe prace za {spec.approved_delta_cents} groszy netto w pierwszej transzy."
            evidence_id = add_document(kind, title, body)
            evidence_ids.append(evidence_id)
            db.execute(
                "INSERT INTO changes (stage_id, tranche_id, document_id, kind, delta_cents, approved) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (case_id, first_tranche_id, evidence_id, change_kind, spec.approved_delta_cents),
            )
        elif category == "invoice_or_estimate_error":
            evidence_ids.append(add_document(
                "email", f"Wyjaśnienie faktury {project_code}",
                f"W fakturze projektu {project_code} omyłkowo dodano "
                f"{spec.invoice_cents - baseline} groszy netto. Prosimy o korektę faktury.",
            ))
        elif category == "unknown":
            add_document(
                "email", f"Wiadomość bez potwierdzenia {project_code}",
                "Proszę sprawdzić dokumentację projektu. Nie potwierdzam żadnej zmiany ceny.",
            )

        vat_cents = spec.invoice_cents * 23 // 100
        retention_cents = spec.invoice_cents // 10 if category == "staged_billing" else 0
        db.execute(
            "INSERT INTO invoices (id, client_id, project_id, tranche_id, issued_on, number, net_cents, vat_cents, retention_cents) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (case_id, client_id, case_id, first_tranche_id, issue_date, f"FV/{issue_date[:4]}/{case_id:03d}",
             spec.invoice_cents, vat_cents, retention_cents),
        )
        db.execute(
            "INSERT INTO invoice_items (invoice_id, description, net_cents, vat_cents) "
            "VALUES (?, ?, ?, ?)",
            (case_id, "Pierwsza transza projektu", spec.invoice_cents, vat_cents),
        )
        labels.append({
            "case_id": project_code,
            "client_id": client_id,
            "project_id": case_id,
            "invoice_id": case_id,
            "expected_cause": spec.expected_cause,
            "expected_difference_cents": spec.invoice_cents - baseline,
            "evidence_document_ids": evidence_ids if category != "unknown" else [],
        })

    db.commit()
    return labels

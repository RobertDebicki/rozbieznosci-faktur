"""API rozróżnia brak faktur, zgodność i rzeczywiste rozbieżności."""

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from rozbieznosci.app import create_app
from rozbieznosci.db import open_db, seed_demo
from rozbieznosci.indeks import index_documents


class EmptyEmbedder:
    def encode(self, texts):
        return [[] for _ in texts]


def test_analysis_and_case_api(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.sqlite"
    db = open_db(db_path)
    try:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        index_documents(db, tmp_path / "docs", embedder=EmptyEmbedder())
    finally:
        db.close()
    client = TestClient(create_app(db_path, today=date(2026, 9, 22)))
    created = client.post("/api/analyses", json={"question": "Pokaż rozbieżności z ostatniego roku"})
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["status"] == "discrepancies"
    assert body["filters"]["date_from"] == "2025-09-22"
    assert len(body["cases"]) == 30
    assert sum(item["status"] == "difference" for item in body["cases"]) == 25
    fetched = client.get(f"/api/analyses/{body['id']}")
    assert fetched.json() == body
    detail = client.get(f"/api/analyses/{body['id']}/cases/2")
    assert detail.status_code == 200
    assert detail.json()["explanation"]["cause"] == "approved_change"
    assert detail.json()["explanation"]["evidence_ids"]


def test_no_invoices_and_no_discrepancies_are_distinct(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.sqlite"
    db = open_db(db_path)
    try:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        index_documents(db, tmp_path / "docs", embedder=EmptyEmbedder())
    finally:
        db.close()
    client = TestClient(create_app(db_path, today=date(2026, 9, 22)))
    none = client.post("/api/analyses", json={"date_from": "2024-01-01", "date_to": "2024-12-31"})
    assert none.json()["status"] == "no_invoices"
    equal = client.post("/api/analyses", json={"date_from": "2026-09-15", "date_to": "2026-09-15"})
    assert equal.json()["status"] == "no_discrepancies"
    high_threshold = client.post(
        "/api/analyses",
        json={"date_from": "2025-09-22", "date_to": "2026-09-22",
              "min_difference_cents": 999_999_999},
    )
    assert high_threshold.json()["status"] == "no_discrepancies"


def test_ambiguous_question_requests_clarification(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.sqlite"
    db = open_db(db_path)
    try:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
    finally:
        db.close()
    client = TestClient(create_app(db_path, today=date(2026, 9, 22)))
    response = client.post("/api/analyses", json={"question": "Faktury klienta Firma Demo"})
    assert response.status_code == 409
    assert response.json()["options"]

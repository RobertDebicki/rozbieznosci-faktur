"""Główna ścieżka użytkownika jest czytelna w przeglądarce."""

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from rozbieznosci.app import create_app
from rozbieznosci.db import open_db, seed_demo
from rozbieznosci.indeks import index_documents


class EmptyEmbedder:
    def encode(self, texts):
        return [[] for _ in texts]


def _client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "demo.sqlite"
    db = open_db(db_path)
    try:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        index_documents(db, tmp_path / "docs", embedder=EmptyEmbedder())
    finally:
        db.close()
    return TestClient(create_app(db_path, today=date(2026, 9, 22)))


def test_start_has_question_and_accessible_filters(tmp_path: Path) -> None:
    page = _client(tmp_path).get("/")
    assert page.status_code == 200
    assert "O co chcesz zapytać?" in page.text
    assert '<label for="question"' in page.text
    assert '<label for="date-from"' in page.text
    assert "Sprawdź rozbieżności" in page.text


def test_results_and_detail_show_numbers_and_real_source(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created = client.post("/api/analyses", json={"question": "Pokaż rozbieżności z ostatniego roku"}).json()
    results = client.get(f"/analyses/{created['id']}")
    assert results.status_code == 200
    assert "Tak zrozumieliśmy Twoje pytanie" in results.text
    assert "Rozbieżności" in results.text
    detail = client.get(f"/analyses/{created['id']}/cases/2")
    assert detail.status_code == 200
    assert "Jak policzyliśmy różnicę" in detail.text
    assert "2 400,00" in detail.text
    assert "Dowody w dokumentach" in detail.text
    assert "Otwórz źródło" in detail.text
    assert "<dialog" in detail.text
    source_id = next(item for item in created["cases"] if item["invoice_id"] == 2)["sources"][0]["chunk_id"]
    source = client.get(f"/api/analyses/{created['id']}/cases/2/sources/{source_id}")
    assert source.status_code == 200
    assert "Zatwierdzono zmianę zakresu" in source.json()["text"]
    assert client.get(f"/api/analyses/{created['id']}/cases/2/sources/999999").status_code == 404
    assert f"/analyses/{created['id']}" in client.get("/history").text
    assert "Jak zapytać o faktury?" in client.get("/help").text


def test_empty_states_are_distinct_and_unknown_has_no_source_button(tmp_path: Path) -> None:
    client = _client(tmp_path)
    none = client.post("/api/analyses", json={"date_from": "2024-01-01", "date_to": "2024-12-31"}).json()
    assert "Nie znaleziono faktur" in client.get(f"/analyses/{none['id']}").text
    equal = client.post("/api/analyses", json={"date_from": "2026-09-15", "date_to": "2026-09-15"}).json()
    assert "Nie znaleziono rozbieżności" in client.get(f"/analyses/{equal['id']}").text
    all_cases = client.post("/api/analyses", json={"question": "Pokaż rozbieżności z ostatniego roku"}).json()
    unknown = client.get(f"/analyses/{all_cases['id']}/cases/6")
    assert "Przyczyna nieustalona" in unknown.text
    assert "Otwórz źródło" not in unknown.text

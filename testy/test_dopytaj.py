"""Pytania uzupełniające korzystają wyłącznie z zapisanej analizy."""

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from rozbieznosci.app import create_app
from rozbieznosci.db import open_db, seed_demo
from rozbieznosci.dopytaj import answer_followup
from rozbieznosci.indeks import index_documents
from rozbieznosci.model import DemoProvider


class EmptyEmbedder:
    def encode(self, texts):
        return [[] for _ in texts]


def _analysis(tmp_path: Path):
    db_path = tmp_path / "demo.sqlite"
    db = open_db(db_path)
    seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
    index_documents(db, tmp_path / "docs", embedder=EmptyEmbedder())
    db.close()
    client = TestClient(create_app(db_path, today=date(2026, 9, 22)))
    analysis = client.post("/api/analyses", json={"question": "Pokaż rozbieżności z ostatniego roku"}).json()
    return client, db_path, analysis


def test_largest_difference_is_computed_from_current_result(tmp_path: Path) -> None:
    _, path, analysis = _analysis(tmp_path)
    db = open_db(path)
    try:
        answer = answer_followup(analysis["id"], None, "Która rozbieżność jest największa?", db, DemoProvider())
        biggest = max(
            (item for item in analysis["cases"] if item["status"] == "difference"),
            key=lambda item: abs(item["difference_cents"]),
        )
        assert answer.status == "answered"
        assert answer.case_id == biggest["invoice_id"]
        assert biggest["invoice_number"] in answer.text
    finally:
        db.close()


def test_case_cause_cites_only_its_source(tmp_path: Path) -> None:
    _, path, analysis = _analysis(tmp_path)
    db = open_db(path)
    try:
        answer = answer_followup(analysis["id"], 2, "Dlaczego ta faktura jest wyższa?", db, DemoProvider())
        case = next(item for item in analysis["cases"] if item["invoice_id"] == 2)
        assert answer.status == "answered"
        assert answer.source_ids == tuple(case["explanation"]["evidence_ids"])
        assert case["explanation"]["quotes"][0] in answer.text
    finally:
        db.close()


def test_new_scope_and_unsupported_question_do_not_guess(tmp_path: Path) -> None:
    _, path, analysis = _analysis(tmp_path)
    db = open_db(path)
    try:
        other = answer_followup(analysis["id"], None, "Sprawdź klienta XYZ z poprzedniego roku", db, DemoProvider())
        assert other.status == "new_analysis_required"
        vague = answer_followup(analysis["id"], None, "Czy można zaksięgować?", db, DemoProvider())
        assert vague.status == "cannot_answer"
    finally:
        db.close()


def test_api_persists_followup_and_history(tmp_path: Path) -> None:
    client, _, analysis = _analysis(tmp_path)
    created = client.post(
        f"/api/analyses/{analysis['id']}/questions",
        json={"case_id": 2, "question": "Dlaczego ta faktura jest wyższa?"},
    )
    assert created.status_code == 200
    assert created.json()["source_ids"]
    history = client.get(f"/api/analyses/{analysis['id']}/questions")
    assert len(history.json()) == 1
    assert history.json()[0]["question"] == "Dlaczego ta faktura jest wyższa?"
    page = client.get(f"/analyses/{analysis['id']}/cases/2")
    assert "Masz pytanie do tej sprawy?" in page.text

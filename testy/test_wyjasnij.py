"""Wyjaśnienia wolno przyjąć tylko z istniejącym dowodem."""

from datetime import date
from pathlib import Path

import pytest

from rozbieznosci.db import open_db, seed_demo
from rozbieznosci.detektor import detect
from rozbieznosci.indeks import index_documents
from rozbieznosci.model import DemoProvider, ModelReply
from rozbieznosci.models import Detection
from rozbieznosci.szukaj import EvidenceChunk
from rozbieznosci.wyjasnij import explain


@pytest.fixture
def detection() -> Detection:
    return Detection(2, 2, 2, 3, date(2026, 9, 1), 2_320_000,
                     2_320_000, 2_080_000, 2_320_000, 240_000, 0, "difference")


@pytest.fixture
def chunks() -> list[EvidenceChunk]:
    return [EvidenceChunk(
        5, 12, "akapit 1",
        "Aneks nr 1. Zatwierdzono zmianę zakresu pierwszej transzy o 240000 groszy netto.",
        "dane/syntetyczne/DEMO-002-amendment-3.txt", 0.05,
    )]


class FakeProvider:
    def __init__(self, payload: dict | Exception):
        self.payload = payload
        self.called = False

    def complete_json(self, messages: list[dict], schema: dict) -> ModelReply:
        self.called = True
        if isinstance(self.payload, Exception):
            raise self.payload
        return ModelReply(self.payload, input_tokens=100, output_tokens=30)


def valid_payload() -> dict:
    return {
        "cause": "approved_change",
        "difference_cents": 240_000,
        "evidence": [{"chunk_id": 12, "quote": "Zatwierdzono zmianę zakresu pierwszej transzy o 240000 groszy netto."}],
    }


def test_accepts_real_quote_and_copies_amount_from_detection(detection, chunks) -> None:
    provider = FakeProvider(valid_payload())
    result = explain(detection, chunks, provider)
    assert provider.called
    assert result.cause == "approved_change"
    assert result.evidence_ids == (12,)
    assert result.quotes[0] in chunks[0].text
    assert result.difference_cents == 240_000
    assert "2 400,00 zł" in result.text


@pytest.mark.parametrize("change", [
    {"evidence": [{"chunk_id": 999, "quote": "Zatwierdzono zmianę zakresu"}]},
    {"evidence": [{"chunk_id": 12, "quote": "Nieistniejące potwierdzenie"}]},
    {"difference_cents": 999_999},
    {"cause": "tax_fraud"},
    {"cause": "discount"},
])
def test_rejects_unverifiable_claims(detection, chunks, change) -> None:
    payload = valid_payload() | change
    result = explain(detection, chunks, FakeProvider(payload))
    assert result.cause == "unknown"
    assert result.evidence_ids == ()
    assert result.difference_cents == 240_000
    assert result.reason_unknown


def test_no_evidence_or_provider_error_returns_unknown(detection) -> None:
    provider = FakeProvider(valid_payload())
    assert explain(detection, [], provider).cause == "unknown"
    assert not provider.called
    assert explain(detection, [], FakeProvider(TimeoutError("timeout"))).reason_unknown


def test_unknown_model_reply_still_counts_model_usage(detection, chunks) -> None:
    payload = valid_payload() | {"cause": "unknown", "evidence": []}
    result = explain(detection, chunks, FakeProvider(payload))
    assert result.cause == "unknown"
    assert result.input_tokens == 100
    assert result.output_tokens == 30


def test_equal_invoice_needs_no_model(detection, chunks) -> None:
    equal = Detection(**(detection.__dict__ | {"raw_difference_cents": 0, "status": "equal"}))
    provider = FakeProvider(valid_payload())
    result = explain(equal, chunks, provider)
    assert result.cause == "staged_billing"
    assert not provider.called


def test_demo_provider_explains_synthetic_cases_without_api_key(tmp_path: Path) -> None:
    class EmptyEmbedder:
        def encode(self, texts):
            return [[] for _ in texts]

    db = open_db(tmp_path / "demo.sqlite")
    try:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        index_documents(db, tmp_path / "docs", embedder=EmptyEmbedder())
        detections = detect(db, None, date(2025, 1, 1), date(2027, 1, 1))
        causes = []
        for item in detections:
            rows = db.execute(
                "SELECT c.document_id, c.id, c.locator, c.text, d.path "
                "FROM document_chunks c JOIN documents d ON d.id = c.document_id "
                "WHERE d.project_id = ? ORDER BY c.id",
                (item.project_id,),
            ).fetchall()
            evidence = [EvidenceChunk(*row, score=0.0) for row in rows]
            causes.append(explain(item, evidence, DemoProvider()).cause)
        assert causes.count("staged_billing") == 5
        assert causes.count("approved_change") == 5
        assert causes.count("discount") == 5
        assert causes.count("extra_work") == 5
        assert causes.count("invoice_or_estimate_error") == 5
        assert causes.count("unknown") == 5
    finally:
        db.close()

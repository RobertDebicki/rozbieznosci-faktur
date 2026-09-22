"""Raport mierzy znane etykiety bez zawyżania mianowników."""

import json
from datetime import date
from pathlib import Path

from rozbieznosci.db import open_db, seed_demo
from rozbieznosci.indeks import index_documents
from rozbieznosci.model import DemoProvider
from skrypty.ewaluuj import evaluate, main


class EmptyEmbedder:
    def encode(self, texts):
        return [[] for _ in texts]


def test_full_synthetic_set_meets_declared_targets(tmp_path: Path) -> None:
    db = open_db(tmp_path / "demo.sqlite")
    try:
        labels = seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        index_documents(db, tmp_path / "docs", embedder=EmptyEmbedder())
        report = evaluate(db, labels, DemoProvider())
        assert report["cases_total"] == 30
        assert report["amounts"]["correct"] == 30
        assert report["amounts"]["accuracy_pct"] == 100.0
        assert report["with_evidence"]["total"] == 20
        assert report["with_evidence"]["correct_explanations"] == 20
        assert report["with_evidence"]["accuracy_pct"] == 100.0
        assert report["without_evidence"]["total"] == 5
        assert report["without_evidence"]["correct_unknown"] == 5
        assert report["staged_billing"]["correctly_not_flagged"] == 5
        assert report["staged_billing"]["total"] == 5
        assert report["fictitious_sources"] == 0
        assert "indeksowania" in report["latency_ms"]["scope"]
        assert all(report["targets_met"].values())
    finally:
        db.close()


def test_empty_category_has_null_percentage_not_zero(tmp_path: Path) -> None:
    db = open_db(tmp_path / "demo.sqlite")
    try:
        labels = seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        index_documents(db, tmp_path / "docs", embedder=EmptyEmbedder())
        report = evaluate(db, [labels[0]], DemoProvider())
        assert report["with_evidence"]["total"] == 0
        assert report["with_evidence"]["accuracy_pct"] is None
        assert report["without_evidence"]["accuracy_pct"] is None
    finally:
        db.close()


def test_cli_writes_report_to_requested_path(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.sqlite"
    labels_path = tmp_path / "labels.jsonl"
    output = tmp_path / "report.json"
    db = open_db(db_path)
    try:
        labels = seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        index_documents(db, tmp_path / "docs", embedder=EmptyEmbedder())
    finally:
        db.close()
    labels_path.write_text("".join(json.dumps(item) + "\n" for item in labels), encoding="utf-8")
    main(["--db", str(db_path), "--dataset", str(labels_path), "--output", str(output)])
    assert json.loads(output.read_text(encoding="utf-8"))["cases_total"] == 30

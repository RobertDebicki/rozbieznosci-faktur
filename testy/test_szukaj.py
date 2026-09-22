"""Wyszukiwanie dowodów z izolacją projektów i jawną dostępnością."""

from datetime import date
from pathlib import Path
import subprocess
import sys

from rozbieznosci.db import open_db, seed_demo
from rozbieznosci.indeks import index_documents
from rozbieznosci.szukaj import retrieve


class TinyEmbedder:
    """Kontrolowany wektor testowy dla parafrazy, bez pobierania modelu."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            words = text.casefold()
            vectors.append([
                float("rabat" in words or "obniżk" in words),
                float("aneks" in words or "zakresu" in words),
                float("protokół" in words or "prace" in words),
            ])
        return vectors


def test_exact_amendment_number_and_amount_are_found(tmp_path: Path) -> None:
    db = open_db(tmp_path / "demo.sqlite")
    try:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        count = index_documents(db, tmp_path / "docs", embedder=TinyEmbedder())
        assert count == 85
        doc = db.execute(
            "SELECT d.id, d.title, c.delta_cents FROM changes c "
            "JOIN documents d ON d.id = c.document_id WHERE c.kind = 'scope' LIMIT 1"
        ).fetchone()
        doc_id, title, delta = doc
        project_id = db.execute("SELECT project_id FROM documents WHERE id = ?", (doc_id,)).fetchone()[0]
        results = retrieve(db, project_id, f"{title} {delta}", embedder=TinyEmbedder())
        assert results[0].document_id == doc_id
        assert str(delta) in results[0].text
        assert results[0].locator.startswith("akapit ")
        assert Path(results[0].source_path).is_file()
    finally:
        db.close()


def test_semantic_paraphrase_and_project_isolation(tmp_path: Path) -> None:
    db = open_db(tmp_path / "demo.sqlite")
    try:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        index_documents(db, tmp_path / "docs", embedder=TinyEmbedder())
        # Projekt 3 ma potwierdzony rabat. Pytanie używa innej frazy.
        results = retrieve(db, 3, "obniżka ceny", embedder=TinyEmbedder())
        assert results
        assert "rabat" in results[0].text.casefold()
        assert all(
            db.execute("SELECT project_id FROM documents WHERE id = ?", (item.document_id,)).fetchone()[0] == 3
            for item in results
        )
        assert retrieve(db, 999, "rabat", embedder=TinyEmbedder()) == []
    finally:
        db.close()


def test_unavailable_document_is_reported_without_invented_chunk(tmp_path: Path) -> None:
    db = open_db(tmp_path / "demo.sqlite")
    try:
        seed_demo(db, corpus_dir=tmp_path / "docs", as_of=date(2026, 9, 22))
        document_id, path = db.execute(
            "SELECT id, path FROM documents WHERE project_id = 2 AND kind = 'amendment'"
        ).fetchone()
        Path(path).unlink()
        index_documents(db, tmp_path / "docs", embedder=TinyEmbedder())
        assert db.execute("SELECT available FROM documents WHERE id = ?", (document_id,)).fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM document_chunks WHERE document_id = ?", (document_id,)).fetchone()[0] == 0
        assert all(item.document_id != document_id for item in retrieve(db, 2, "aneks", embedder=TinyEmbedder()))
    finally:
        db.close()


def test_index_is_repeatable_and_cli_runs_without_model(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.sqlite"
    corpus = tmp_path / "docs"
    db = open_db(db_path)
    try:
        seed_demo(db, corpus_dir=corpus, as_of=date(2026, 9, 22))
        first = index_documents(db, corpus, embedder=TinyEmbedder())
        second = index_documents(db, corpus, embedder=TinyEmbedder())
        assert first == second == 85
        assert db.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0] == 85
    finally:
        db.close()
    result = subprocess.run(
        [sys.executable, "-m", "skrypty.indeksuj", "--db", str(db_path),
         "--corpus", str(corpus), "--fts-only"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Zaindeksowano fragmenty: 85" in result.stdout
    db = open_db(db_path)
    try:
        assert retrieve(db, 2, "Aneks nr 1")
    finally:
        db.close()

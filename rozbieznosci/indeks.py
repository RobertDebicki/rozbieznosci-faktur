"""Wsadowy indeks fragmentów dokumentów demonstracyjnych."""

from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Protocol


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Lokalny model wielojęzyczny, ładowany dopiero przy indeksowaniu lub pytaniu."""

    def __init__(self) -> None:
        self.model = self._load_model()

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_model():
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Brakuje lokalnego modelu. Zainstaluj zależności: uv sync --extra retrieval"
            ) from exc
        return SentenceTransformer(MODEL_NAME)

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


def _paragraphs(text: str, max_chars: int = 1200) -> list[str]:
    result: list[str] = []
    for paragraph in (part.strip() for part in text.split("\n\n")):
        if not paragraph:
            continue
        while len(paragraph) > max_chars:
            cut = paragraph.rfind(" ", 0, max_chars)
            if cut < max_chars // 2:
                cut = max_chars
            result.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        if paragraph:
            result.append(paragraph)
    return result


def index_documents(
    db: sqlite3.Connection,
    corpus_dir: Path,
    *,
    embedder: Embedder | None = None,
) -> int:
    """Odczytaj lokalny korpus i zastąp indeks jednym spójnym przebiegiem."""
    corpus = Path(corpus_dir).resolve()
    prepared: list[tuple[int, str, str, str]] = []
    unavailable: list[int] = []
    for document_id, title, source_path in db.execute(
        "SELECT id, title, path FROM documents ORDER BY id"
    ).fetchall():
        path = Path(source_path).resolve()
        if not path.is_relative_to(corpus) or not path.is_file():
            unavailable.append(document_id)
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            unavailable.append(document_id)
            continue
        paragraphs = _paragraphs(body)
        if not paragraphs:
            unavailable.append(document_id)
            continue
        for number, paragraph in enumerate(paragraphs, 1):
            prepared.append((document_id, f"akapit {number}", f"{title}\n{paragraph}", source_path))

    if not prepared:
        vectors: list[list[float]] = []
    else:
        provider = embedder or SentenceTransformerEmbedder()
        vectors = provider.encode([item[2] for item in prepared])
        if len(vectors) != len(prepared):
            raise ValueError("Model zwrócił inną liczbę wektorów niż fragmentów.")

    with db:
        db.execute("DELETE FROM document_fts")
        db.execute("DELETE FROM document_chunks")
        db.execute("UPDATE documents SET available = 1")
        db.executemany("UPDATE documents SET available = 0 WHERE id = ?", [(item,) for item in unavailable])
        for (document_id, locator, text, _), vector in zip(prepared, vectors):
            cursor = db.execute(
                "INSERT INTO document_chunks (document_id, locator, text, embedding_json) "
                "VALUES (?, ?, ?, ?)",
                (document_id, locator, text, json.dumps([float(value) for value in vector])),
            )
            db.execute(
                "INSERT INTO document_fts (rowid, chunk_id, text) VALUES (?, ?, ?)",
                (cursor.lastrowid, cursor.lastrowid, text),
            )
    return len(prepared)

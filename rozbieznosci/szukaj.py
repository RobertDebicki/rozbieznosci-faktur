"""Hybrydowe wyszukiwanie fragmentów z filtrem projektu."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass

from .indeks import Embedder, SentenceTransformerEmbedder


@dataclass(frozen=True)
class EvidenceChunk:
    document_id: int
    chunk_id: int
    locator: str
    text: str
    source_path: str
    score: float


def _similarity(first: list[float], second: list[float]) -> float:
    if len(first) != len(second) or not first:
        return 0.0
    norm = math.sqrt(sum(value * value for value in first)) * math.sqrt(
        sum(value * value for value in second)
    )
    return sum(a * b for a, b in zip(first, second)) / norm if norm else 0.0


def retrieve(
    db: sqlite3.Connection,
    project_id: int,
    query: str,
    limit: int = 8,
    *,
    embedder: Embedder | None = None,
) -> list[EvidenceChunk]:
    """Połącz dokładne trafienia FTS5 i podobieństwo wektorów w obrębie projektu."""
    if limit < 1 or not query.strip():
        return []
    rows = db.execute(
        "SELECT c.id, c.document_id, c.locator, c.text, d.path, c.embedding_json "
        "FROM document_chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE d.project_id = ? AND d.available = 1 ORDER BY c.id",
        (project_id,),
    ).fetchall()
    if not rows:
        return []
    scores: dict[int, float] = {}
    terms = re.findall(r"\w+", query, flags=re.UNICODE)
    if terms:
        match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        lexical = db.execute(
            "SELECT f.rowid FROM document_fts f "
            "JOIN document_chunks c ON c.id = f.rowid "
            "JOIN documents d ON d.id = c.document_id "
            "WHERE document_fts MATCH ? AND d.project_id = ? AND d.available = 1 "
            "ORDER BY bm25(document_fts) LIMIT ?",
            (match, project_id, max(limit * 4, 20)),
        ).fetchall()
        for rank, (chunk_id,) in enumerate(lexical, 1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (60 + rank)

    embedded_rows = []
    for row in rows:
        if row[5]:
            vector = json.loads(row[5])
            if vector:
                embedded_rows.append((row[0], vector))
    if embedded_rows:
        provider = embedder or SentenceTransformerEmbedder()
        query_vector = [float(value) for value in provider.encode([query])[0]]
        semantic = sorted(
            (
                (_similarity(query_vector, vector), chunk_id)
                for chunk_id, vector in embedded_rows
            ),
            reverse=True,
        )
        for rank, (similarity, chunk_id) in enumerate(
            ((score, chunk_id) for score, chunk_id in semantic if score > 0), 1
        ):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (60 + rank)

    by_id = {row[0]: row for row in rows}
    ranked_ids = sorted(scores, key=lambda item: (-scores[item], item))[:limit]
    return [
        EvidenceChunk(row[1], row[0], row[2], row[3], row[4], scores[chunk_id])
        for chunk_id in ranked_ids
        for row in [by_id[chunk_id]]
    ]

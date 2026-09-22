"""Zbuduj indeks dokumentów z lokalnego korpusu syntetycznego."""

from __future__ import annotations

import argparse
from pathlib import Path

from rozbieznosci.db import open_db
from rozbieznosci.indeks import index_documents


class _NoEmbedding:
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[] for _ in texts]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("dane/demo.sqlite"))
    parser.add_argument("--corpus", type=Path, default=Path("dane/syntetyczne"))
    parser.add_argument(
        "--fts-only", action="store_true",
        help="Indeksuj tylko dokładne frazy, bez pobierania modelu semantycznego",
    )
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error(f"Brak bazy {args.db}. Najpierw uruchom skrypty.generuj_dane.")
    db = open_db(args.db)
    try:
        count = index_documents(
            db, args.corpus, embedder=_NoEmbedding() if args.fts_only else None
        )
        unavailable = db.execute(
            "SELECT COUNT(*) FROM documents WHERE available = 0"
        ).fetchone()[0]
    finally:
        db.close()
    print(f"Zaindeksowano fragmenty: {count}")
    print(f"Dokumenty niedostępne: {unavailable}")
    print("Tryb: tylko pełnotekstowy" if args.fts_only else "Tryb: pełnotekstowy i semantyczny")


if __name__ == "__main__":
    main()

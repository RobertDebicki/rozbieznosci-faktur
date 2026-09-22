"""Utwórz syntetyczną bazę, korpus i zestaw ewaluacyjny."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from rozbieznosci.db import open_db, seed_demo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("dane/demo.sqlite"))
    parser.add_argument("--corpus", type=Path, default=Path("dane/syntetyczne"))
    parser.add_argument("--evaluation", type=Path, default=Path("ewaluacja/zestaw.jsonl"))
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    db = open_db(args.db)
    try:
        labels = seed_demo(db, seed=args.seed, corpus_dir=args.corpus, as_of=args.as_of)
    finally:
        db.close()

    args.evaluation.parent.mkdir(parents=True, exist_ok=True)
    args.evaluation.write_text(
        "".join(json.dumps(label, ensure_ascii=False) + "\n" for label in labels),
        encoding="utf-8",
    )
    print(f"Utworzono {len(labels)} syntetycznych spraw w {args.db}")


if __name__ == "__main__":
    main()

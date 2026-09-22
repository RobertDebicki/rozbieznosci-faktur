"""Zmierz pełny przepływ na etykietowanym zestawie syntetycznym."""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import date
from pathlib import Path

from rozbieznosci.db import open_db
from rozbieznosci.detektor import detect
from rozbieznosci.model import DemoProvider, GroqProvider, LLMProvider
from rozbieznosci.pomiary import percentage, percentile_ms
from rozbieznosci.szukaj import EVIDENCE_QUERY, retrieve
from rozbieznosci.wyjasnij import explain


def evaluate(db: sqlite3.Connection, labels: list[dict], provider: LLMProvider) -> dict:
    """Porównaj obliczenia i wyjaśnienia z etykietami; licz jawne mianowniki."""
    if db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] and not db.execute(
        "SELECT 1 FROM document_chunks LIMIT 1"
    ).fetchone():
        raise ValueError("Najpierw zaindeksuj dokumenty poleceniem skrypty.indeksuj.")
    rows = db.execute("SELECT MIN(issued_on), MAX(issued_on) FROM invoices").fetchone()
    detections = {}
    if rows[0]:
        detections = {item.invoice_id: item for item in detect(
            db, None, date.fromisoformat(rows[0]), date.fromisoformat(rows[1])
        )}
    amount_correct = explanation_correct = unknown_correct = fictitious = retrieval_hits = 0
    with_evidence = without_evidence = staged = staged_correct = 0
    input_tokens = output_tokens = 0
    timings: list[float] = []
    details = []
    for label in labels:
        started = time.perf_counter()
        detection = detections.get(label["invoice_id"])
        if detection is None:
            details.append({"case_id": label["case_id"], "error": "Brak faktury w bazie"})
            continue
        amount_ok = detection.raw_difference_cents == label["expected_difference_cents"]
        amount_correct += int(amount_ok)
        chunks = retrieve(db, detection.project_id, EVIDENCE_QUERY, limit=8) if detection.status == "difference" else []
        explanation = explain(detection, chunks, provider)
        evidence_expected = label["expected_cause"] not in {"unknown", "none"}
        if evidence_expected:
            with_evidence += 1
            explanation_correct += int(explanation.cause == label["expected_cause"])
            retrieval_hits += int(any(chunk.document_id in label["evidence_document_ids"] for chunk in chunks))
        elif label["expected_cause"] == "unknown":
            without_evidence += 1
            unknown_correct += int(explanation.cause == "unknown" and not explanation.evidence_ids)
        else:
            staged += 1
            staged_correct += int(detection.status == "equal" and explanation.cause == "staged_billing")
        indexed = {chunk.chunk_id: chunk for chunk in chunks}
        for chunk_id, quote in zip(explanation.evidence_ids, explanation.quotes):
            chunk = indexed.get(chunk_id)
            if chunk is None or chunk.document_id not in label["evidence_document_ids"] or quote not in chunk.text:
                fictitious += 1
        if len(explanation.evidence_ids) != len(explanation.quotes):
            fictitious += abs(len(explanation.evidence_ids) - len(explanation.quotes))
        input_tokens += explanation.input_tokens
        output_tokens += explanation.output_tokens
        duration_ms = (time.perf_counter() - started) * 1000
        timings.append(duration_ms)
        details.append({
            "case_id": label["case_id"], "expected_cause": label["expected_cause"],
            "predicted_cause": explanation.cause, "amount_correct": amount_ok,
            "evidence_ids": list(explanation.evidence_ids),
            "duration_ms": round(duration_ms, 2),
        })
    mode = "demo_simulation" if isinstance(provider, DemoProvider) else "external_api"
    targets = {
        "all_amounts_correct": amount_correct == len(labels),
        "no_fictitious_sources": fictitious == 0,
        "at_least_90_pct_explanations_with_evidence": bool(with_evidence) and explanation_correct / with_evidence >= .9,
        "at_least_5_unknown_cases_correct": without_evidence >= 5 and unknown_correct == without_evidence,
        "no_false_staged_alarms": staged >= 5 and staged_correct == staged,
    }
    return {
        "mode": mode,
        "cases_total": len(labels),
        "amounts": {"correct": amount_correct, "total": len(labels),
                    "accuracy_pct": percentage(amount_correct, len(labels))},
        "with_evidence": {"correct_explanations": explanation_correct,
                          "total": with_evidence,
                          "accuracy_pct": percentage(explanation_correct, with_evidence),
                          "retrieval_hits": retrieval_hits,
                          "retrieval_recall_pct": percentage(retrieval_hits, with_evidence)},
        "without_evidence": {"correct_unknown": unknown_correct, "total": without_evidence,
                             "accuracy_pct": percentage(unknown_correct, without_evidence)},
        "staged_billing": {"correctly_not_flagged": staged_correct, "total": staged,
                           "accuracy_pct": percentage(staged_correct, staged)},
        "fictitious_sources": fictitious,
        "latency_ms": {"total": round(sum(timings), 2),
                       "p50": percentile_ms(timings, .5),
                       "p95": percentile_ms(timings, .95),
                       "scope": "Czas samej analizy spraw; bez generowania bazy, indeksowania i renderowania UI"},
        "model_usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                        "estimated_cost_usd": 0.0 if mode == "demo_simulation" else None,
                        "cost_note": "Symulacja bez zewnętrznego API" if mode == "demo_simulation"
                        else "Brak aktualnej stawki modelu w konfiguracji"},
        "targets_met": targets,
        "cases": details,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("dane/demo.sqlite"))
    parser.add_argument("--dataset", type=Path, default=Path("ewaluacja/zestaw.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("ewaluacja/wyniki/raport.json"))
    parser.add_argument("--provider", choices=("demo", "groq"), default="demo")
    args = parser.parse_args(argv)
    if not args.db.is_file():
        parser.error(f"Brak bazy {args.db}.")
    if not args.dataset.is_file():
        parser.error(f"Brak zestawu {args.dataset}.")
    labels = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    provider = DemoProvider() if args.provider == "demo" else GroqProvider()
    db = open_db(args.db)
    try:
        report = evaluate(db, labels, provider)
    finally:
        db.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Sprawy: {report['cases_total']}")
    print(f"Kwoty poprawne: {report['amounts']['correct']}/{report['amounts']['total']}")
    print(f"Wyjaśnienia z dowodem: {report['with_evidence']['correct_explanations']}/{report['with_evidence']['total']}")
    print(f"Przyczyna nieustalona: {report['without_evidence']['correct_unknown']}/{report['without_evidence']['total']}")
    print(f"Fikcyjne źródła: {report['fictitious_sources']}")
    print(f"Raport: {args.output}")


if __name__ == "__main__":
    main()

"""API analiz rozbieżności dla demonstracyjnego interfejsu."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .db import open_db
from .detektor import detect
from .model import DemoProvider, LLMProvider
from .models import Client
from .pytanie import AnalysisRequest, Clarification, months_before, parse_request
from .szukaj import retrieve
from .wyjasnij import explain


class AnalysisInput(BaseModel):
    question: str | None = None
    client_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_difference_pct: Decimal = Field(default=Decimal(0), ge=0)
    min_difference_cents: int = Field(default=0, ge=0)


def create_app(
    db_path: Path,
    *,
    today: date | None = None,
    provider: LLMProvider | None = None,
) -> FastAPI:
    app = FastAPI(title="Rozbieżności faktur", version="0.1.0")
    path = Path(db_path)
    current_day = today or date.today()
    explanation_provider = provider or DemoProvider()

    @app.post("/api/analyses")
    def create_analysis(payload: AnalysisInput):
        if not path.is_file():
            raise HTTPException(503, "Brak bazy demonstracyjnej.")
        db = open_db(path)
        try:
            clients = [Client(row[0], row[1]) for row in db.execute("SELECT id, name FROM clients ORDER BY name")]
            if payload.question:
                parsed = parse_request(payload.question, current_day, clients)
                if isinstance(parsed, Clarification):
                    return JSONResponse(
                        status_code=409,
                        content={"message": parsed.message, "options": list(parsed.options)},
                    )
                filters = parsed
            else:
                date_from = payload.date_from or months_before(current_day, 12)
                date_to = payload.date_to or current_day
                if date_from > date_to:
                    raise HTTPException(422, "Data początkowa jest późniejsza od końcowej.")
                if payload.client_id is not None and payload.client_id not in {item.id for item in clients}:
                    raise HTTPException(422, "Nieznany klient.")
                filters = AnalysisRequest(
                    payload.client_id, date_from, date_to,
                    payload.min_difference_pct, payload.min_difference_cents,
                )

            invoice_count = db.execute(
                "SELECT COUNT(*) FROM invoices WHERE issued_on >= ? AND issued_on <= ? "
                "AND (? IS NULL OR client_id = ?)",
                (filters.date_from.isoformat(), filters.date_to.isoformat(),
                 filters.client_id, filters.client_id),
            ).fetchone()[0]
            detections = detect(
                db, filters.client_id, filters.date_from, filters.date_to,
                filters.min_difference_cents, filters.min_difference_pct,
            )
            cases = []
            for detection in detections:
                invoice = db.execute(
                    "SELECT number FROM invoices WHERE id = ?", (detection.invoice_id,)
                ).fetchone()[0]
                chunks = retrieve(
                    db, detection.project_id,
                    "aneks rabat prace dodatkowe omyłkowo zmiana zakresu", limit=8,
                ) if detection.status == "difference" else []
                explanation = explain(detection, chunks, explanation_provider)
                cases.append({
                    "invoice_id": detection.invoice_id,
                    "invoice_number": invoice,
                    "project_id": detection.project_id,
                    "client_id": detection.client_id,
                    "issued_on": detection.issued_on.isoformat(),
                    "status": detection.status,
                    "invoice_net_cents": detection.invoice_net_cents,
                    "baseline_cents": detection.baseline_cents,
                    "reference_cents": detection.reference_cents,
                    "difference_cents": detection.raw_difference_cents,
                    "adjusted_difference_cents": detection.adjusted_difference_cents,
                    "explanation": asdict(explanation),
                    "sources": [
                        {"chunk_id": chunk.chunk_id, "document_id": chunk.document_id,
                         "locator": chunk.locator, "text": chunk.text,
                         "source_path": chunk.source_path}
                        for chunk in chunks if chunk.chunk_id in explanation.evidence_ids
                    ],
                })
            if invoice_count == 0:
                status = "no_invoices"
            elif not cases:
                status = "no_discrepancies"
            elif any(case["status"] == "difference" for case in cases):
                status = "discrepancies"
            elif any(case["status"] == "not_comparable" for case in cases):
                status = "needs_review"
            else:
                status = "no_discrepancies"
            result = {
                "status": status,
                "question": payload.question,
                "filters": {
                    "client_id": filters.client_id,
                    "date_from": filters.date_from.isoformat(),
                    "date_to": filters.date_to.isoformat(),
                    "min_difference_pct": str(filters.min_difference_pct),
                    "min_difference_cents": filters.min_difference_cents,
                },
                "cases": cases,
            }
            with db:
                cursor = db.execute(
                    "INSERT INTO analyses (result_json) VALUES (?)",
                    ("{}",),
                )
                result["id"] = cursor.lastrowid
                db.execute(
                    "UPDATE analyses SET result_json = ? WHERE id = ?",
                    (json.dumps(result, ensure_ascii=False), result["id"]),
                )
            return result
        finally:
            db.close()

    @app.get("/api/analyses/{analysis_id}")
    def get_analysis(analysis_id: int):
        if not path.is_file():
            raise HTTPException(404, "Nie znaleziono analizy.")
        db = open_db(path)
        try:
            row = db.execute(
                "SELECT result_json FROM analyses WHERE id = ?", (analysis_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Nie znaleziono analizy.")
            return json.loads(row[0])
        finally:
            db.close()

    @app.get("/api/analyses/{analysis_id}/cases/{case_id}")
    def get_case(analysis_id: int, case_id: int):
        result = get_analysis(analysis_id)
        for case in result["cases"]:
            if case["invoice_id"] == case_id:
                return case
        raise HTTPException(404, "Nie znaleziono sprawy w tej analizie.")

    return app

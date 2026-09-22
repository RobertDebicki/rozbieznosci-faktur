"""API analiz rozbieżności dla demonstracyjnego interfejsu."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .db import open_db
from .detektor import detect
from .dopytaj import answer_followup
from .model import DemoProvider, LLMProvider
from .models import Client
from .pytanie import AnalysisRequest, Clarification, months_before, parse_request
from .szukaj import retrieve
from .wyjasnij import explain
from .wyjasnij import _pln


class AnalysisInput(BaseModel):
    question: str | None = None
    client_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_difference_pct: Decimal = Field(default=Decimal(0), ge=0)
    min_difference_cents: int = Field(default=0, ge=0)


class FollowupInput(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    case_id: int | None = None


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
    asset_dir = Path(__file__).parent
    templates = Jinja2Templates(directory=str(asset_dir / "templates"))
    templates.env.filters["pln"] = _pln
    app.mount("/static", StaticFiles(directory=asset_dir / "static"), name="static")

    @app.get("/")
    def start_page(request: Request):
        clients = []
        if path.is_file():
            db = open_db(path)
            try:
                clients = db.execute("SELECT id, name FROM clients ORDER BY name").fetchall()
            finally:
                db.close()
        return templates.TemplateResponse(request, "start.html", {
            "clients": clients,
            "date_from": months_before(current_day, 12).isoformat(),
            "date_to": current_day.isoformat(),
        })

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

    @app.get("/api/analyses/{analysis_id}/cases/{case_id}/sources/{chunk_id}")
    def get_source(analysis_id: int, case_id: int, chunk_id: int):
        case = get_case(analysis_id, case_id)
        for source in case["sources"]:
            if source["chunk_id"] == chunk_id:
                return {"document_id": source["document_id"],
                        "locator": source["locator"], "text": source["text"]}
        raise HTTPException(404, "Źródło nie należy do tej sprawy.")

    def _followups(analysis_id: int, case_id: int | None = None) -> list[dict]:
        db = open_db(path)
        try:
            rows = db.execute(
                "SELECT id, case_id, question, answer_json FROM followups "
                "WHERE analysis_id = ? AND (? IS NULL OR case_id = ?) ORDER BY id",
                (analysis_id, case_id, case_id),
            ).fetchall()
            return [{"id": row[0], "question": row[2],
                     **json.loads(row[3])} for row in rows]
        finally:
            db.close()

    @app.post("/api/analyses/{analysis_id}/questions")
    def ask_followup(analysis_id: int, payload: FollowupInput):
        if not path.is_file():
            raise HTTPException(404, "Nie znaleziono analizy.")
        db = open_db(path)
        try:
            try:
                answer = answer_followup(
                    analysis_id, payload.case_id, payload.question, db, explanation_provider
                )
            except ValueError as exc:
                raise HTTPException(404, str(exc)) from exc
            result = asdict(answer)
            with db:
                cursor = db.execute(
                    "INSERT INTO followups (analysis_id, case_id, question, answer_json) "
                    "VALUES (?, ?, ?, ?)",
                    (analysis_id, payload.case_id, payload.question,
                     json.dumps(result, ensure_ascii=False)),
                )
            return {"id": cursor.lastrowid, "question": payload.question, **result}
        finally:
            db.close()

    @app.get("/api/analyses/{analysis_id}/questions")
    def list_followups(analysis_id: int):
        get_analysis(analysis_id)
        return _followups(analysis_id)

    @app.get("/analyses/{analysis_id}")
    def results_page(request: Request, analysis_id: int):
        analysis = get_analysis(analysis_id)
        return templates.TemplateResponse(request, "results.html", {
            "analysis": analysis, "followups": _followups(analysis_id),
        })

    @app.get("/analyses/{analysis_id}/cases/{case_id}")
    def case_page(request: Request, analysis_id: int, case_id: int):
        analysis = get_analysis(analysis_id)
        case = get_case(analysis_id, case_id)
        return templates.TemplateResponse(request, "case.html", {
            "analysis": analysis, "case": case,
            "followups": _followups(analysis_id, case_id),
        })

    @app.get("/history")
    def history_page(request: Request):
        analyses = []
        if path.is_file():
            db = open_db(path)
            try:
                for row in db.execute(
                    "SELECT id, created_at, result_json FROM analyses ORDER BY id DESC LIMIT 30"
                ):
                    item = json.loads(row[2])
                    analyses.append({"id": row[0], "created_at": row[1],
                                     "status": item["status"], "filters": item["filters"],
                                     "count": len(item["cases"])})
            finally:
                db.close()
        return templates.TemplateResponse(request, "history.html", {"analyses": analyses})

    @app.get("/help")
    def help_page(request: Request):
        return templates.TemplateResponse(request, "help.html", {})

    return app


app = create_app(Path(os.environ.get("DEMO_DB_PATH", "dane/demo.sqlite")))

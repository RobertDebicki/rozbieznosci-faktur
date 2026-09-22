"""Wymienny dostawca odpowiedzi JSON dla wyjaśniacza."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ModelReply:
    data: dict
    input_tokens: int = 0
    output_tokens: int = 0
    elapsed_ms: int = 0


class LLMProvider(Protocol):
    def complete_json(self, messages: list[dict], schema: dict) -> ModelReply: ...


class DemoProvider:
    """Jawna symulacja odpowiedzi modelu na syntetycznych frazach, bez API."""

    def complete_json(self, messages: list[dict], schema: dict) -> ModelReply:
        prompt = messages[-1]["content"]
        difference = re.search(r"\bdifference_cents=(-?\d+)", prompt)
        if not difference:
            raise ValueError("Brak kwoty z detektora w żądaniu.")
        patterns = (
            ("approved_change", "zatwierdzono zmianę zakresu"),
            ("discount", "zatwierdzili rabat"),
            ("extra_work", "odebrano dodatkowe prace"),
            ("invoice_or_estimate_error", "omyłkowo dodano"),
        )
        for match in re.finditer(r"chunk_id=(\d+): (.*?)(?=\nchunk_id=|\Z)", prompt, re.DOTALL):
            chunk_text = match.group(2).strip()
            for cause, phrase in patterns:
                if phrase in chunk_text.casefold():
                    quote = chunk_text.split("\n", 1)[-1].strip()
                    return ModelReply({
                        "cause": cause,
                        "difference_cents": int(difference.group(1)),
                        "evidence": [{"chunk_id": int(match.group(1)), "quote": quote}],
                    })
        return ModelReply({
            "cause": "unknown",
            "difference_cents": int(difference.group(1)),
            "evidence": [],
        })


class GroqProvider:
    """Mały adapter HTTP. Klucz pobiera tylko ze środowiska procesu."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Brak GROQ_API_KEY w środowisku.")
        self.model = model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

    def complete_json(self, messages: list[dict], schema: dict) -> ModelReply:
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "invoice_explanation", "strict": False, "schema": schema},
            },
        }).encode("utf-8")
        request = Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.monotonic()
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
        elapsed_ms = round((time.monotonic() - started) * 1000)
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage") or {}
        return ModelReply(
            json.loads(content),
            int(usage.get("prompt_tokens") or 0),
            int(usage.get("completion_tokens") or 0),
            elapsed_ms,
        )

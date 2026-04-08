from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "knowledge.json"
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="DriverX Chatbot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    suggestions: list[str] = []
    matched_intent: str | None = None


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def load_knowledge() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return {
            "fallback": (
                "I can help with plans, account support, coverage, activation, billing, "
                "fleet support, and speaking with a real person."
            ),
            "default_suggestions": [
                "Check out plans",
                "Get help with my account",
                "Ask about coverage",
                "Talk to a real person",
            ],
            "intents": [],
        }

    with DATA_PATH.open(encoding="utf-8-sig") as file:
        data = json.load(file)

    data.setdefault("fallback", "Could you share a bit more detail?")
    data.setdefault("default_suggestions", [])
    data.setdefault("intents", [])
    return data


def score_intent(query: str, keywords: list[str]) -> int:
    if not keywords:
        return 0

    score = 0
    query_tokens = set(query.split())
    padded_query = f" {query} "

    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if not normalized_keyword:
            continue

        if f" {normalized_keyword} " in padded_query:
            score += max(3, len(normalized_keyword.split()) * 2)
            continue

        keyword_tokens = normalized_keyword.split()
        overlap = sum(1 for token in keyword_tokens if token in query_tokens)
        if overlap == len(keyword_tokens) and len(keyword_tokens) > 1:
            score += overlap * 2
        elif len(keyword_tokens) == 1 and overlap == 1:
            score += 1

    return score


knowledge = load_knowledge()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "driverx-chatbot-api",
        "knowledge_path": str(DATA_PATH),
        "frontend_available": FRONTEND_DIR.joinpath("index.html").exists(),
        "intent_count": len(knowledge.get("intents", [])),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(payload: MessageRequest) -> ChatResponse:
    raw_message = (payload.message or "").strip()
    if not raw_message:
        return ChatResponse(
            response=knowledge.get("fallback", "How can I help you?"),
            suggestions=knowledge.get("default_suggestions", []),
        )

    normalized = normalize_text(raw_message)

    activation_phrases = (
        "activate sim",
        "sim activation",
        "activate esim",
        "esim activation",
        "activate my sim",
    )
    if any(phrase in normalized for phrase in activation_phrases):
        activation_intent = next(
            (intent for intent in knowledge.get("intents", []) if intent.get("id") == "activation"),
            None,
        )
        if activation_intent:
            return ChatResponse(
                response=activation_intent.get("response", knowledge.get("fallback", "How can I help you?")),
                suggestions=activation_intent.get("suggestions", []),
                matched_intent="activation",
            )

    no_service_phrases = (
        "no service",
        "no signal",
        "bars but no data",
        "no bars",
    )
    if any(phrase in normalized for phrase in no_service_phrases):
        no_service_intent = next(
            (intent for intent in knowledge.get("intents", []) if intent.get("id") == "no_service_troubleshooting"),
            None,
        )
        if no_service_intent:
            return ChatResponse(
                response=no_service_intent.get("response", knowledge.get("fallback", "How can I help you?")),
                suggestions=no_service_intent.get("suggestions", []),
                matched_intent="no_service_troubleshooting",
            )

    zip_match = re.search(r"\b\d{5,6}\b", raw_message)
    if zip_match:
        return ChatResponse(
            response=(
                f"Thanks! For exact coverage around {zip_match.group(0)}, check the map here:\n"
                "https://mvnoc.ai/coverage-map\n\n"
                "We run on Tier-1 nationwide coverage, and most drivers report solid service "
                "in cities, suburbs, and highways."
            ),
            suggestions=["Check coverage map", "City / metro", "Rural / highways", "Talk to support"],
            matched_intent="coverage_zip",
        )

    best_match: dict[str, Any] | None = None
    best_score = 0

    for intent in knowledge.get("intents", []):
        score = score_intent(normalized, intent.get("keywords", []))
        if score > best_score:
            best_score = score
            best_match = intent

    if best_match and best_score >= 2:
        return ChatResponse(
            response=best_match.get("response", knowledge.get("fallback", "How can I help you?")),
            suggestions=best_match.get("suggestions", []),
            matched_intent=best_match.get("id"),
        )

    return ChatResponse(
        response=knowledge.get("fallback", "How can I help you?"),
        suggestions=knowledge.get("default_suggestions", []),
    )


if FRONTEND_DIR.exists():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")


@app.get("/")
def serve_frontend() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_path)

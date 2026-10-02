"""
FBR Tax FAQ RAG Chatbot — Phase 5: Backend API

Usage:
    uvicorn app.main:app --reload
"""

import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from groq import APIConnectionError, APITimeoutError, RateLimitError

from app.auth import get_current_user
from app.model import ChatRequest, ChatResponse, HealthResponse, Source
from app.rag import get_corpus_size, run_pipeline
from generate import EmptyAnswerError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fbr_chatbot")

app = FastAPI(
    title="FBR Tax FAQ RAG Chatbot",
    description="Answers general FBR tax law/procedure questions from public FBR documents only. "
                "Never looks up personal tax status, filing history, or account data.",
    version="1.0.0",
)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config", include_in_schema=False)
def config():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase config missing in .env")
    return {"supabase_url": url, "supabase_key": key}


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", corpus_chunks=get_corpus_size())


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    try:
        result = run_pipeline(request.question)
    except RateLimitError:
        logger.warning("Groq rate limit hit")
        raise HTTPException(status_code=429, detail="The service is busy right now. Please try again in a moment.")
    except (APITimeoutError, APIConnectionError):
        logger.warning("Groq unreachable or timed out")
        raise HTTPException(status_code=503, detail="The answer service is temporarily unavailable. Please try again.")
    except EmptyAnswerError:
        logger.warning("Empty completion from Groq")
        raise HTTPException(status_code=502, detail="Couldn't generate an answer this time. Please try again.")
    except Exception:
        logger.exception("Pipeline failure (question length=%d)", len(request.question))
        raise HTTPException(status_code=500, detail="Internal error processing the question.")

    return ChatResponse(
        answer=result["answer"],
        sources=[Source(**s) for s in result.get("sources", [])],
        covered=result.get("covered", True),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error."})
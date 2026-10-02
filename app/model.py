"""Pydantic schemas for the FBR Tax FAQ chatbot API."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints


class ChatRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class Source(BaseModel):
    marker: str
    chunk_id: str
    title: str
    source_url: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    covered: bool  # False when the model refused / flagged out-of-corpus


class HealthResponse(BaseModel):
    status: str
    corpus_chunks: int
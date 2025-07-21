from os import getenv
from typing import List, Optional

from pydantic import UUID4, BaseModel


class ChatMessage(BaseModel):
    type: str  # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    query: str
    model: str = getenv("LLM_MODEL")
    user: Optional[str] = None
    matomo_client_id: Optional[UUID4] = None
    control_number: Optional[int] = None
    history: Optional[List[ChatMessage]] = None


class Citation(BaseModel):
    doc_id: int
    control_number: int
    snippet: str


class QueryResponse(BaseModel):
    brief_answer: str
    long_answer: str
    citations: List[Citation]
    trace_id: str


class QueryPaperResponse(BaseModel):
    long_answer: str
    trace_id: str

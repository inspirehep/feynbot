from os import getenv
from typing import List, Optional

from pydantic import UUID4, BaseModel


class QueryRequest(BaseModel):
    query: str
    model: str = getenv("LLM_MODEL")
    user: Optional[str] = None
    matomo_client_id: Optional[UUID4] = None


class Citation(BaseModel):
    doc_id: int
    control_number: int
    snippet: str


class QueryResponse(BaseModel):
    brief_answer: str
    long_answer: str
    citations: List[Citation]

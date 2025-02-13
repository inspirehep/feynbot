from os import getenv
from typing import Optional

from pydantic import UUID4, BaseModel


class QueryRequest(BaseModel):
    query: str
    model: str = getenv("LLM_MODEL")
    user: Optional[str] = None
    matomo_client_id: Optional[UUID4] = None

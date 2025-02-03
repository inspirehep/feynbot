from typing import Optional

from pydantic import UUID4, BaseModel


class QueryRequest(BaseModel):
    query: str
    model: str = "llama3.1:8b-instruct-fp16"
    user: Optional[str] = None
    matomo_client_id: Optional[UUID4] = None

from typing import Optional

from pydantic import UUID4, BaseModel


class QueryRequest(BaseModel):
    query: str
    model: str = "llama3.2"
    user: str
    matomo_client_id: Optional[UUID4] = None

from typing import Optional

from pydantic import UUID4, BaseModel


class SearchFeedbackRequest(BaseModel):
    question: str
    additional: Optional[str] = None
    matomo_client_id: Optional[UUID4] = None

from pydantic import BaseModel
from typing import Optional


class FeedbackRequest(BaseModel):
    id: str
    rating: bool
    comment: Optional[str] = None

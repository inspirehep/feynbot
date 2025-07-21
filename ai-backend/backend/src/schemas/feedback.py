from typing import Optional

from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    rating: bool
    comment: Optional[str] = None


class RagFeedbackRequest(BaseModel):
    trace_id: str
    helpful: bool
    comment: Optional[str] = None
    score_id: Optional[str] = None


class RagFeedbackResponse(BaseModel):
    score_id: str

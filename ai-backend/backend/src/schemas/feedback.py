from typing import Optional

from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    rating: bool
    comment: Optional[str] = None

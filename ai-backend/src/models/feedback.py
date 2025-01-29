import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Feedback(Base):
    __tablename__ = "feedback"

    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries_ir.id"), primary_key=True
    )
    rating: Mapped[bool] = mapped_column()
    comment: Mapped[Optional[str]] = mapped_column()

    __table_args__ = (Index("idx_feedback_rating", "rating"),)

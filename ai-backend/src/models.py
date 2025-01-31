import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ARRAY, ForeignKey, Index, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class QueryIr(Base):
    __tablename__ = "queries_ir"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    query: Mapped[str] = mapped_column()
    brief: Mapped[str] = mapped_column()
    response: Mapped[str] = mapped_column()
    references: Mapped[list[str]] = mapped_column(
        ARRAY(String)
    )  # Need to specify ARRAY type for pgsql
    expanded_query: Mapped[str] = mapped_column()
    model: Mapped[str] = mapped_column()
    backend_version: Mapped[Optional[str]] = mapped_column()
    matomo_client_id: Mapped[Optional[uuid.UUID]] = mapped_column()
    user: Mapped[str] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
    response_time: Mapped[float] = mapped_column()

    __table_args__ = (Index("idx_queries_ir_timestamp", "timestamp"),)


class Feedback(Base):
    __tablename__ = "feedback"

    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries_ir.id"), primary_key=True
    )
    rating: Mapped[bool] = mapped_column()
    comment: Mapped[Optional[str]] = mapped_column()

    __table_args__ = (Index("idx_feedback_rating", "rating"),)

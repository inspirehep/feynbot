import csv
import logging
import time
from datetime import datetime
from io import StringIO
from os import getenv
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import UUID4
from requests import Session

from src.database import get_db
from src.ir_pipeline.orchestrator import search
from src.models import Feedback, QueryIr
from src.schemas.feedback import FeedbackRequest
from src.schemas.query import QueryRequest

logger = logging.getLogger(__name__)

security = HTTPBasic()

router = APIRouter(
    tags=["v1"],
    responses={404: {"description": "Not found"}},
)


def authenticate(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    valid_username = getenv("EXPORT_AUTH_USERNAME")
    valid_password = getenv("EXPORT_AUTH_PASSWORD")

    if not (
        credentials.username == valid_username
        and credentials.password == valid_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@router.post("/query")
async def save_query(request: QueryRequest, db: Session = Depends(get_db)):
    VALID_MODELS = getenv("VALID_MODELS").split(",")
    if request.model not in VALID_MODELS:
        logger.error(f"Invalid model requested: {request.model}")
        raise HTTPException(
            status_code=400,
            detail="Invalid model name, available models are: "
            + ", ".join(VALID_MODELS),
        )

    start_time = time.time()
    query_response = search(request.query, request.model, use_highlights=True)
    response_time = time.time() - start_time

    query_ir = QueryIr(
        query=request.query,
        brief=query_response.get("brief", ""),
        response=query_response.get("response", ""),
        references=query_response.get("references", []),
        expanded_query=query_response.get("expanded_query", ""),
        model=request.model,
        backend_version=getenv("BACKEND_VERSION"),
        matomo_client_id=request.matomo_client_id,
        user=request.user,
        response_time=response_time,
    )

    try:
        db.add(query_ir)
        db.commit()
        db.refresh(query_ir)
    except Exception as e:
        logger.error(f"Database error when saving query_ir: {str(e)}", exc_info=True)
        db.rollback()

    return {}


@router.get("/query/{query_id}")
async def get_query(query_id: UUID4, db: Session = Depends(get_db)):
    query = db.query(QueryIr).filter(QueryIr.id == query_id).first()
    if not query:
        logger.warning(f"Query not found: {query_id}")
        raise HTTPException(status_code=404, detail="Query not found")
    return query


@router.put("/query/{query_id}/feedback")
async def upsert_feedback(
    query_id: UUID4, request: FeedbackRequest, db: Session = Depends(get_db)
):
    """Creates or updates feedback for a query. Hence using a put method."""
    # Check if query exists
    query = db.query(QueryIr).filter(QueryIr.id == query_id).first()
    if not query:
        logger.warning(f"Query not found for feedback: {query_id}")
        raise HTTPException(status_code=404, detail="Query not found")

    # Update or create feedback
    feedback = db.query(Feedback).filter(Feedback.query_id == query_id).first()
    if feedback:
        feedback.rating = request.rating
        feedback.comment = request.comment
    else:
        feedback = Feedback(
            query_id=query_id,
            rating=request.rating,
            comment=request.comment,
        )
        db.add(feedback)

    try:
        db.commit()
        db.refresh(feedback)
    except Exception as e:
        logger.error(f"Database error when saving feedback: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Database error when saving feedback: {str(e)}"
        )

    return feedback


@router.get("/query/{query_id}/feedback")
async def get_feedback(query_id: UUID4, db: Session = Depends(get_db)):
    feedback = db.query(Feedback).filter(Feedback.query_id == query_id).first()
    if not feedback:
        logger.warning(f"Feedback not found for query ID: {query_id}")
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback


@router.get("/export-ir")
async def export_queries(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
    _: str = Depends(authenticate),
):
    """Export queries_ir in CSV format within the specified date range."""
    queries = (
        db.query(QueryIr)
        .filter(QueryIr.timestamp >= start_date, QueryIr.timestamp <= end_date)
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)

    columns = [column.name for column in QueryIr.__table__.columns]
    writer.writerow(columns)

    for query in queries:
        writer.writerow([getattr(query, column) for column in columns])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=queries_ir_{start_date.date()}_{end_date.date()}.csv"
        },
    )

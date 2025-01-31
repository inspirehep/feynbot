import time
from os import getenv

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4
from requests import Session

from src.database import get_db
from src.ir_pipeline.app import search
from src.models import Feedback, QueryIr
from src.schemas.feedback import FeedbackRequest
from src.schemas.query import QueryRequest

router = APIRouter(
    tags=["v1"],
    responses={404: {"description": "Not found"}},
)


@router.post("/query")
async def save_query(request: QueryRequest, db: Session = Depends(get_db)):
    VALID_MODELS = getenv("VALID_MODELS").split(",")
    if request.model not in VALID_MODELS:
        raise HTTPException(
            status_code=400,
            detail="Invalid model name, available models are: "
            + ", ".join(VALID_MODELS),
        )

    start_time = time.time()
    query_response = search(request.query)
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
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Database error when saving query_ir: {str(e)}"
        )

    return query_ir


@router.get("/query/{query_id}")
async def get_query(query_id: UUID4, db: Session = Depends(get_db)):
    query = db.query(QueryIr).filter(QueryIr.id == query_id).first()
    if not query:
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
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Database error when saving feedback: {str(e)}"
        )

    return feedback


@router.get("/query/{query_id}/feedback")
async def get_feedback(query_id: UUID4, db: Session = Depends(get_db)):
    feedback = db.query(Feedback).filter(Feedback.query_id == query_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback

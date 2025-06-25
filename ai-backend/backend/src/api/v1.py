import csv
import logging
import time
from datetime import datetime
from io import StringIO
from os import getenv
from typing import Annotated

from backend.src.database import SessionLocal, get_db
from backend.src.ir_pipeline.orchestrator import search, search_playground
from backend.src.ir_pipeline.schema import Terms
from backend.src.ir_pipeline.tools.inspire import InspireOSFullTextSearchTool
from backend.src.models import Feedback, QueryIr, SearchFeedback
from backend.src.rag_pipeline.rag_pipeline import search_rag
from backend.src.rag_pipeline.schemas import QueryResponse
from backend.src.schemas.feedback import FeedbackRequest
from backend.src.schemas.query import QueryRequest
from backend.src.schemas.search_feedback import SearchFeedbackRequest
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import UUID4
from requests import Session

logger = logging.getLogger("uvicorn")

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


async def process_query_task(request: QueryRequest):
    try:
        start_time = time.time()

        query_response = await search(
            request.query,
            request.model,
            user=str(request.matomo_client_id),
            use_highlights=True,
        )

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

        with SessionLocal() as db:
            try:
                db.add(query_ir)
                db.commit()
                db.refresh(query_ir)
            except Exception as e:
                logger.error(
                    f"Database error when saving query_ir: {str(e)}", exc_info=True
                )
                db.rollback()

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)


@router.post("/query")
async def save_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(process_query_task, request)

    return {}


@router.post("/query-playground")
async def playground_query(request: QueryRequest):
    """Returns responses in a format suitable for the playground."""
    response = await search_playground(request.query, request.model)
    return response


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
        ) from e

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
            "Content-Disposition": (
                f"attachment; filename=queries_ir_"
                f"{start_date.date()}_{end_date.date()}.csv"
            )
        },
    )


@router.post("/query-os")
async def query_os(
    terms: Terms,
    size: int = 5,
    _: str = Depends(authenticate),
):
    """Send query to OpenSearch endpoint and return its response with highlights."""
    inspire_search_tool = InspireOSFullTextSearchTool(size=size)
    raw_results = inspire_search_tool.run(terms)
    return {"results": raw_results}


@router.post("/search-feedback")
async def create_search_feedback(
    request: SearchFeedbackRequest,
    db: Session = Depends(get_db),
):
    """Creates a new search feedback entry."""
    feedback = SearchFeedback(
        question=request.question,
        additional=request.additional,
        matomo_client_id=request.matomo_client_id,
    )

    try:
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
    except Exception as e:
        logger.error(
            f"Database error when saving search feedback: {str(e)}", exc_info=True
        )
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error when saving search feedback: {str(e)}",
        ) from e

    return {}


@router.get("/export-search-feedback")
async def export_feedback(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
    export_csv: bool = False,
    _: str = Depends(authenticate),
):
    """Export search feedback within date range. In CSV format if csv=True."""
    feedbacks = (
        db.query(SearchFeedback)
        .filter(
            SearchFeedback.timestamp >= start_date, SearchFeedback.timestamp <= end_date
        )
        .all()
    )

    if csv:
        output = StringIO()
        writer = csv.writer(output)

        columns = [column.name for column in SearchFeedback.__table__.columns]
        writer.writerow(columns)

        for feedback in feedbacks:
            writer.writerow([getattr(feedback, column) for column in columns])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=search_feedback_"
                    f"{start_date.date()}_{end_date.date()}.csv"
                )
            },
        )
    else:
        return feedbacks


@router.post("/query-rag", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Process a query using the RAG pipeline and return the response with citations.
    """
    try:
        logger.info("[query_rag] Received RAG query: %s", request.query)
        return search_rag(request.query, request.model)
    except Exception as e:
        logger.error(f"Error processing RAG query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing RAG query: {str(e)}"
        ) from e

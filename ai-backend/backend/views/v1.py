from fastapi import APIRouter, HTTPException
from ..schemas.feedback import FeedbackRequest
from ..schemas.query import QueryRequest
from ..config import VALID_MODELS
from ..ir_pipeline.app import search

router = APIRouter(
    tags=["v1"],
    responses={404: {"description": "Not found"}},
)


@router.post("/query")
async def query_model(request: QueryRequest):
    if request.model_name not in VALID_MODELS:
        raise HTTPException(
            status_code=400,
            detail="Invalid model name, available models are: "
            + ", ".join(VALID_MODELS),
        )
    query_response = search(request.query)
    return {"query": query_response, "model": request.model_name}


@router.post("/feedback")
async def send_feedback(feedback: FeedbackRequest):
    return {
        "feedback_id": feedback.id,
        "rating": feedback.rating,
        "comment": feedback.comment,
    }

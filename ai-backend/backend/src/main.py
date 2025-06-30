import logging
from os import getenv

from backend.src.api import v1
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

logging.basicConfig(format="%(levelname)s - %(name)s:%(lineno)d - %(message)s")

app = FastAPI(root_path=getenv("ROOT_PATH", ""))

app.include_router(v1.router, prefix="/v1")

allowed_origins = getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

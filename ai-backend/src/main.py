import logging
from os import getenv

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from src.api import v1

logging.basicConfig(format="%(levelname)s - %(name)s:%(lineno)d - %(message)s")

app = FastAPI(root_path=getenv("ROOT_PATH", ""))

app.include_router(v1.router, prefix="/v1")

Instrumentator().instrument(app).expose(app)

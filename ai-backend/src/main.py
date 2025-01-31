from os import getenv

from fastapi import FastAPI

from .api import v1

app = FastAPI(root_path=getenv("ROOT_PATH", ""))

app.include_router(v1.router, prefix="/v1")

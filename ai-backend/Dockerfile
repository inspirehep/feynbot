FROM python:3.11-buster AS builder
RUN pip install poetry==1.8.3
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR


FROM python:3.11-slim AS dev
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    FASTAPI_ENV=development
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
WORKDIR /app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


FROM dev AS prod
ARG BACKEND_VERSION
ENV BACKEND_VERSION=${BACKEND_VERSION}
ENV ROOT_PATH=/ai
COPY src/ /app/src/
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

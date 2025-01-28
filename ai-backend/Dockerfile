FROM python:3.11-buster AS builder
RUN pip install poetry==1.8.3
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache
WORKDIR /backend
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR


FROM python:3.11-slim AS dev
ENV VIRTUAL_ENV=/backend/.venv \
    PATH="/backend/.venv/bin:$PATH" \
    FASTAPI_ENV=development
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
WORKDIR /backend
EXPOSE 8000
EXPOSE 80
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

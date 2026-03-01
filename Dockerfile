FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true && \
    poetry install --only main --no-interaction --no-ansi

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY src/ src/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]

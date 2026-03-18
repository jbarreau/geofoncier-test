FROM python:3.12-slim
WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir poetry

COPY lib/ /lib
COPY backend/auth-service/pyproject.toml backend/auth-service/poetry.lock ./
RUN poetry install --no-root --without dev

COPY backend/auth-service/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim
WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir poetry

COPY lib/ /lib
COPY backend/task-service/pyproject.toml backend/task-service/poetry.lock ./
RUN poetry install --no-root --without dev

COPY backend/task-service/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

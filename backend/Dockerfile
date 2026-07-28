FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

RUN groupadd --gid 10001 predictionlab \
    && useradd \
        --uid 10001 \
        --gid predictionlab \
        --create-home \
        --shell /usr/sbin/nologin \
        predictionlab

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY datasets ./datasets

RUN python -m pip install --no-cache-dir .

USER predictionlab

EXPOSE 8000

CMD ["uvicorn", "predictionlab.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

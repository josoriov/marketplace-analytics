FROM docker.io/library/python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_DEV=1 \
    DBT_ALLOW_EXPERIMENTAL_ADAPTERS=true \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
# dbt v2 loads the PostgreSQL client library at runtime.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall --yes pip \
    && uv sync --locked --no-dev --no-cache

COPY app ./app
COPY dbt ./dbt
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

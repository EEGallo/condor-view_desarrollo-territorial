FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.5

# uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/pipeline

# Venv fuera de /app — el bind mount no lo sobreescribe
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

ENV PATH="/opt/venv/bin:$PATH"

# Código
COPY . .

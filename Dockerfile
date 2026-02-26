# Stage 1: Build dependencies with uv
FROM python:3.12-slim AS builder

# Install uv
RUN pip install uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml ./
COPY uv.lock ./

# Create virtual environment and install deps
RUN uv sync --frozen --no-dev

# Stage 2: Runtime image
FROM python:3.12-slim AS runtime

# Install git (required for RepoSandbox clone operations)
RUN apt-get update && apt-get install -y git --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the venv from builder
COPY --from=builder /app/.venv .venv

# Copy application source
COPY . .

# Activate venv by default
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Ensure reports directory exists
RUN mkdir -p audit/report_onself_generated

CMD ["python", "-m", "src.graph"]

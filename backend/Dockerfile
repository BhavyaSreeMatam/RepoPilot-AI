# Backend image for RepoPilot AI (FastAPI + LangGraph + MCP server subprocess).
# The MCP server is spawned in-process by the app at startup via
# `sys.executable -m app.mcp_server.server`, so no separate container is needed.
FROM python:3.14-slim

# - PYTHONDONTWRITEBYTECODE: no .pyc clutter in the image
# - PYTHONUNBUFFERED: stream logs straight to stdout (better in containers)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer is cached across code-only changes.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application package. WORKDIR=/app means `app` resolves as the
# top-level package, so both `uvicorn app.main:app` and the MCP subprocess
# (`python -m app.mcp_server.server`) work without extra PYTHONPATH tweaks.
COPY app ./app

# OPENAI_API_KEY must be provided at runtime (docker run -e OPENAI_API_KEY=...
# or --env-file). It is intentionally NOT baked into the image.
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

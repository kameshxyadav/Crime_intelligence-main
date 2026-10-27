# ==============================================================================
# Cross-Station Crime Intelligence – Hackathon Submission Container
# Track 1: Solving Fragmented Intelligence | Open Agent Hackathon 2026
# ==============================================================================

# Stage 1: build the React frontend (frontend/dist is gitignored, so a fresh clone has none)
FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    IS_DOCKER=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system utilities (curl for container health checks and evaluation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source code, synthetic data, sample inputs, and built frontend
COPY backend /app/backend
COPY data /app/data
COPY input_examples /app/input_examples
COPY --from=frontend /build/dist /app/frontend/dist
COPY run.py /app/run.py
COPY metadata.json /app/metadata.json
COPY SPONSOR_TECH.md /app/SPONSOR_TECH.md
COPY README.md /app/README.md

# Create persistent state and logs directories
RUN mkdir -p /app/logs /app/.state && chmod -R 777 /app/logs /app/.state

# Set PYTHONPATH to include backend so app can be imported cleanly
ENV PYTHONPATH=/app/backend:/app

EXPOSE 8000

# Health check verifies the FastAPI /api/health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Launch the FastAPI backend on port 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]

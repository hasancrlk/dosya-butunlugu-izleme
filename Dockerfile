# ============================================================
# FIM-Sentinel — Multi-stage Docker build
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="FIM-Sentinel Team"
LABEL description="File Integrity Monitoring & Forensics Tool"

# Create non-root user
RUN groupadd -r sentinel && useradd -r -g sentinel sentinel

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app
COPY . .

# Ensure the app is importable
ENV PYTHONPATH=/app
ENV FIM_DATABASE_URL=postgresql://fim_user:fim_pass@postgres:5432/fim_sentinel

EXPOSE 8000

USER sentinel

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

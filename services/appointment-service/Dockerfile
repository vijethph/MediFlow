# Multi-stage build for Healthcare Appointment Service
# Optimized for security, size, and performance

# Stage 1: Dependencies Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY Pipfile ./

# Install pipenv and dependencies
RUN pip install --no-cache-dir pipenv && \
    pipenv install --system --skip-lock && \
    pip install --no-cache-dir asyncpg && \
    pip uninstall -y pipenv

# Stage 2: Production Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser \
    && mkdir -p /app/common \
    && chown -R appuser:appuser /app

# Copy common directory first (shared code)
COPY --chown=appuser:appuser common/ /app/common/

# Copy application code
COPY --chown=appuser:appuser services/appointment-service/ ./

# Set Python path to include app directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8002

# Health check using curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]


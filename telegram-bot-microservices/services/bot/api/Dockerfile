# Multi-stage build for API service
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/bot/api/requirements.txt .
COPY shared/requirements.txt ./shared-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --user -r shared-requirements.txt && \
    pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r vitte && useradd -r -g vitte vitte

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/vitte/.local

# Copy application code
COPY shared/ ./shared/
COPY services/bot/api/app/ ./app/

# Set ownership to non-root user
RUN chown -R vitte:vitte /app

# Switch to non-root user
USER vitte

# Add local bin to PATH
ENV PATH=/home/vitte/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (internal only)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run with gunicorn + uvicorn workers
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

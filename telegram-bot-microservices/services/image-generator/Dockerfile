FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared directory first (needed for imports)
COPY ./shared /app/shared

# Copy service-specific requirements
COPY ./services/image-generator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY ./services/image-generator/app /app/app
COPY ./services/image-generator/workflows /app/workflows

# Set Python path to include /app for shared imports
ENV PYTHONPATH=/app

CMD ["python", "-m", "celery", "-A", "app.tasks", "worker", "--loglevel=INFO", "--concurrency=2", "--hostname=image-generator@%h", "-Q", "image_generation"]

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the API port
EXPOSE 8989

# Run the FastAPI app. Railway injects PORT; local Docker can fall back to 8989.
CMD ["sh", "-c", "uvicorn pulsepanel_orchestrator.api:app --host 0.0.0.0 --port ${PORT:-8989}"]

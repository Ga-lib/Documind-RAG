FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr,
# which keeps container logs flowing in real time.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first, separately from app code, so Docker's layer
# cache skips this slow step unless requirements.txt actually changed.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application code.
COPY app ./app
COPY scripts ./scripts

# Data directories the app writes to at runtime (uploads, vector DB).
RUN mkdir -p /app/data/uploads /app/data/vector_db

EXPOSE 8000

# Simple healthcheck so `docker ps` and orchestrators can see container status.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
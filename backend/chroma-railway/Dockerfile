FROM python:3.11-slim
WORKDIR /app

# Install chromadb (includes uvicorn)
RUN pip install --no-cache-dir chromadb

# Create data directory (even if not persistent, chroma needs it)
RUN mkdir -p /data && chmod -R 777 /data

# Use uvicorn directly to ensure it binds to 0.0.0.0 and the correct port
CMD uvicorn chromadb.app:app --host 0.0.0.0 --port ${PORT:-8000}

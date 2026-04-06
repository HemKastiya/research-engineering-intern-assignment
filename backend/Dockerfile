FROM python:3.11-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Reduce memory usage
ENV OMP_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false

# HuggingFace cache location
ENV HF_HOME=/app/.cache
ENV TRANSFORMERS_CACHE=/app/.cache

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file (already includes --extra-index-url for CPU)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create cache directory and set permissions for HF user 1000
RUN mkdir -p /app/.cache && chmod -R 777 /app/.cache

# Pre-download embedding model during build
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Copy application
COPY . .

# Set persistent data folder for permissions
RUN chmod -R 777 /app

# HuggingFace default port is 7860
ENV PORT=7860
EXPOSE 7860

# Start FastAPI on port 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
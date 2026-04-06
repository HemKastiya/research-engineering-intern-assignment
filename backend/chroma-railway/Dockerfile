FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir chromadb
RUN mkdir -p /data && chmod -R 777 /data
# Railway provides $PORT, and no brackets [] means it expands correctly
CMD chroma run --host 0.0.0.0 --port $PORT --path /data

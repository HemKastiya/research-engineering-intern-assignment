FROM python:3.11-slim

WORKDIR /app

RUN pip install chromadb

EXPOSE 8000

CMD ["chroma", "run", "--host", "0.0.0.0", "--port", "8000", "--path", "/data"]
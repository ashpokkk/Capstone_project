FROM python:3.14-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/hf_cache

RUN pip install --no-cache-dir torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu

COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
ENV HF_HUB_OFFLINE=1

COPY app ./app
COPY generate.py retrieve.py ./
COPY data/lancedb ./data/lancedb
COPY data/chunks.jsonl ./data/chunks.jsonl

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
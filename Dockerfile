FROM python:3.12-slim
WORKDIR /app

# llama-cpp-python builds native C/C++ code when no compatible wheel is available.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app/backend
ENV PYTHONPATH=/app
ENV JARVIS_DB_PATH=/data/jarvis.db
CMD ["sh","-c","uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

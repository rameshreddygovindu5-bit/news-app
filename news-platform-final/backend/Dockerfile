FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl lxml && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
HEALTHCHECK --interval=15s --timeout=10s --start-period=20s --retries=5 CMD curl -sf http://localhost:8000/health || exit 1
EXPOSE 8000
CMD ["gunicorn","app.main:app","--workers","4","--worker-class","uvicorn.workers.UvicornWorker","--bind","0.0.0.0:8000","--timeout","120"]

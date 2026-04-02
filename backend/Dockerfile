FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr – critical in Docker so that
# Celery worker logs are flushed immediately and the process does not hang
# on blocked I/O during startup.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        # tini provides a proper init process for signal forwarding and zombie
        # reaping — essential for Celery's prefork worker pool in containers.
        tini && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as non-root user — Celery's prefork pool can fail when forking as root
# and the worker emits a SecurityWarning that blocks startup on some systems.
RUN groupadd --system celery && \
    useradd --system --gid celery --home-dir /app celery && \
    chown -R celery:celery /app
USER celery

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

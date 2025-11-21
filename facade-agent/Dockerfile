FROM python:3.12-slim

RUN groupadd --gid 1000 aigroup && \
    useradd --uid 1000 --gid aigroup --shell /bin/bash --create-home aiuser

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN pip install --no-cache-dir hatchling uvicorn[standard]

COPY ./src/ ./src/

RUN pip install --no-cache-dir -e .

RUN mkdir -p /app/logs && \
    chown -R aiuser:aigroup /app

USER aiuser

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

CMD ["uvicorn", "ai_app.app:app", "--host", "0.0.0.0", "--port", "8081"]
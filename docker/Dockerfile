FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /workspace

FROM base AS orchestrator
CMD ["uvicorn", "apps.orchestrator.main:app", "--host", "0.0.0.0", "--port", "8010"]

FROM base AS rag
CMD ["uvicorn", "apps.rag.main:app", "--host", "0.0.0.0", "--port", "8020"]

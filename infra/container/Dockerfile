FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system --gid 10001 fm && \
    useradd --system --uid 10001 --gid fm --home-dir /app --shell /usr/sbin/nologin fm

WORKDIR /app
COPY --chown=fm:fm infra/container/baseline_service.py /app/baseline_service.py

USER 10001:10001

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"]

CMD ["python", "/app/baseline_service.py"]

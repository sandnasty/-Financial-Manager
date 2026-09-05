FROM chainguard/python:latest@sha256:c0e2c76344ef76e57106a4395d2138d58262d87f0e984521df3f7ba8edf3149f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --chown=10001:10001 infra/container/baseline_service.py /app/baseline_service.py

USER 10001:10001

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["/usr/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"]

ENTRYPOINT ["/usr/bin/python"]
CMD ["/app/baseline_service.py"]

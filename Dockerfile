FROM python:3.13-slim-bookworm@sha256:93498f36dc7e24ef233bfdf6cc17d4b8bd32d94ee737143e906460d5f5a914c5 AS dependencies

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt /build/requirements.txt
RUN python -m pip install --require-hashes --only-binary=:all: --no-compile \
    --prefix=/install -r /build/requirements.txt

FROM python:3.13-slim-bookworm@sha256:93498f36dc7e24ef233bfdf6cc17d4b8bd32d94ee737143e906460d5f5a914c5 AS runtime

ARG VCS_REF=development
ARG APP_VERSION=0.1.0
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="pipeline-demo-api" \
      org.opencontainers.image.source="https://github.com/gig0d/enterprise-cicd-pipeline" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    APP_ENVIRONMENT=production APP_BUILD_ID=${VCS_REF} APP_VERSION=${APP_VERSION} \
    PYTHONPATH=/app/src
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --from=dependencies /install /usr/local
RUN python -m pip uninstall --yes pip && \
    python -c "import ensurepip, shutil; from pathlib import Path; shutil.rmtree(Path(ensurepip.__file__).parent)"
COPY --chown=10001:10001 src /app/src
USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2).close()"]
CMD ["python", "-m", "uvicorn", "pipeline_demo_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--timeout-graceful-shutdown", "8"]

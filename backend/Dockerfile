# =============================================================================
# CYBERSLEUTH AI - Backend image
# =============================================================================
# Build from the REPOSITORY ROOT (the API needs supabase/migrations at
# runtime, and Docker cannot copy from outside the build context):
#
#   docker build -t cybersleuth-api -f backend/Dockerfile .
#   docker run -p 8000:8000 --env-file backend/.env cybersleuth-api
#
# The frontend is a static SPA built and served by Netlify; it is not part of
# this image. The API serves JSON, evidence downloads and rendered PDFs.
#
# Configuration: see backend/.env.example. In production set DATABASE_URL
# (privileged, migrations only) and APP_DATABASE_URL (restricted runtime
# role) - see the README's deployment section.
# =============================================================================

FROM python:3.10-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt


FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /srv/backend

# opencv-python-headless still needs glib at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system cybersleuth && useradd --system --gid cybersleuth cybersleuth

COPY --from=builder /install /usr/local
RUN python -m spacy download en_core_web_sm

# Layout note: app's config computes the repository root as the parent of the
# backend directory, so the runtime expects /srv/backend/app and
# /srv/supabase/migrations side by side.
COPY backend/app ./app
COPY supabase/migrations /srv/supabase/migrations

RUN mkdir -p /srv/backend/storage && chown -R cybersleuth:cybersleuth /srv

USER cybersleuth

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT}/api/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

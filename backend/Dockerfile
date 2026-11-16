# =============================================================================
# CYBERSLEUTH AI - Backend image
# =============================================================================
# Build from the REPOSITORY ROOT (the API needs supabase/migrations at
# runtime, and Docker cannot copy from outside the build context):
#
#   docker build -t cybersleuth-api -f backend/Dockerfile .
#   docker run -p 8000:8000 --env-file backend/.env cybersleuth-api
#
# EVERY `COPY` source path below is relative to the REPOSITORY ROOT, because
# the repository root is the build context. Do not change the context to
# `backend/` - the migrations would no longer be reachable.
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

# gcc is only needed if a wheel has to be compiled from source.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt

# -----------------------------------------------------------------------------
# pgserver is a DEVELOPMENT-ONLY dependency.
# -----------------------------------------------------------------------------
# `pgserver` ships a portable embedded PostgreSQL that the local development
# stack uses (see backend/app/database/local_postgres.py). It is still listed
# in backend/requirements.txt - the devcontainer and the local virtualenv
# install that file and must keep working - but it has NO place in a
# production image: it is ~50 MB of unused binaries plus a writable data
# directory that production must never rely on.
#
# It is therefore stripped from the install prefix below. A container built
# from this image ALWAYS needs a real PostgreSQL: set DATABASE_URL (privileged
# connection, migrations only) and APP_DATABASE_URL (restricted runtime role).
#
# When backend/requirements.txt is finally split - see backend/requirements-dev.txt
# for the intended layout - this `rm` becomes unnecessary.
# -----------------------------------------------------------------------------
RUN rm -rf /install/lib/python3.10/site-packages/pgserver* \
    /install/bin/pgserver* \
    /install/share/pgserver*


FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /srv/backend

# System libraries required by the forensic stack:
#   libglib2.0-0  -> opencv-python-headless runtime
#   libsndfile1   -> soundfile / librosa WAV decoding (VoiceProof module)
#   ffmpeg        -> audioread backend for mp3 / m4a / mp4 evidence
#   libgomp1      -> OpenMP runtime used by scipy / scikit-learn (librosa)
#   curl          -> container HEALTHCHECK
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ffmpeg \
        libglib2.0-0 \
        libgomp1 \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system cybersleuth && useradd --system --gid cybersleuth cybersleuth

COPY --from=builder /install /usr/local

# The spaCy model is pinned to an exact version so that two builds of the
# same commit always produce the same model and the same findings.
# 3.8.0 is the en_core_web_sm release that matches spacy==3.8.3.
RUN python -m spacy download en_core_web_sm==3.8.0

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

# syntax=docker/dockerfile:1
# =============================================================================
# CYBERSLEUTH AI - Dev container image (Ubuntu 22.04 + VS Code)
# =============================================================================
# Build context is the REPOSITORY ROOT (the image copies
# `backend/requirements.txt` to bake the Python dependency tree into the
# layer, so rebuilds are instant unless the requirements change):
#
#   docker build -t cybersleuth-dev -f .devcontainer/Dockerfile .
#
# Open this folder in VS Code and choose "Reopen in Container" to get a full
# Ubuntu workspace with Python 3.10, Node 20 and the forensic system
# libraries already installed.
# =============================================================================

FROM ubuntu:22.04

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# --- 1. OS tooling ----------------------------------------------------------
# build-essential/pkg-config  -> source builds if a wheel is missing
# libsndfile1                 -> librosa / soundfile (WAV decoding)
# libglib2.0-0                -> opencv-python-headless runtime
# libicu70                    -> ICU for the bundled PostgreSQL (pgserver)
# ffmpeg                       -> mp3/m4a/mp4 decoding via audioread
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        ffmpeg \
        git \
        gnupg \
        libglib2.0-0 \
        libicu70 \
        libsndfile1 \
        pkg-config \
        python3-pip \
        python3.10 \
        python3.10-dev \
        python3.10-venv \
        sudo \
        wget \
        zip \
    && rm -rf /var/lib/apt/lists/*

# --- 2. Node.js 20 LTS (Vite 5 / React 18 frontend) ------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version \
    && npm --version

# --- 3. Python dependency tree (baked into the image for fast rebuilds) ----
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt \
    && python3.10 -m spacy download en_core_web_sm \
    && rm /tmp/requirements.txt \
    && python3.10 -c "import cv2, librosa, androguard, spacy, fastapi; print('forensic stack OK')"

# --- 4. Non-root development user ------------------------------------------
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && mkdir -p /workspace \
    && chown -R $USERNAME:$USERNAME /workspace /home/$USERNAME

# The devcontainer CLI builds the image as root and drops to $USERNAME in the
# container; the workspace bind-mount is owned by the host user.
USER $USERNAME

WORKDIR /workspace

EXPOSE 3000 8000

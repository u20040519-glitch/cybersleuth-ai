#!/usr/bin/env bash
# =============================================================================
# CYBERSLEUTH AI - dev container bootstrap
# =============================================================================
# Runs once, after the container is created. The heavy Python dependencies are
# already baked into the image; this script makes sure the working tree is in
# sync and installs the frontend dependencies.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "[devcontainer] CyberSleuth AI - Ubuntu workspace ready"
echo "[devcontainer] repository: $REPO_ROOT"
echo "[devcontainer] python: $(python3.10 --version 2>&1) | node: $(node --version)"

# --- Backend ---------------------------------------------------------------
echo "[devcontainer] syncing Python dependencies ..."
python3.10 -m pip install --no-cache-dir -r backend/requirements.txt

echo "[devcontainer] ensuring spaCy model (en_core_web_sm) ..."
python3.10 -m spacy download en_core_web_sm || true

# --- Frontend --------------------------------------------------------------
echo "[devcontainer] installing frontend dependencies ..."
if [ -f frontend/package-lock.json ]; then
    (cd frontend && npm ci --no-audit --no-fund) || (cd frontend && npm install --no-audit --no-fund)
else
    (cd frontend && npm install --no-audit --no-fund)
fi

# --- Sanity check ----------------------------------------------------------
python3.10 - <<'PY'
import importlib
mods = ["fastapi", "cv2", "librosa", "androguard", "spacy", "pgserver", "sqlalchemy"]
missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as exc:  # noqa: BLE001
        missing.append(f"{m} ({exc.__class__.__name__})")
print("[devcontainer] forensic stack:", "OK" if not missing else "MISSING -> " + ", ".join(missing))
PY

echo "[devcontainer] done. Run 'CyberSleuth: start full stack' to launch API + frontend."

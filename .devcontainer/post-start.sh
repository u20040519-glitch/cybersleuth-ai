#!/usr/bin/env bash
# =============================================================================
# CYBERSLEUTH AI - dev container banner
# =============================================================================
# Printed every time the container starts, so the forwarded URLs are always
# one glance away.
# =============================================================================
cat <<'BANNER'

  CyberSleuth AI - Ubuntu dev container

    API      http://localhost:8000/docs
    Frontend http://localhost:3000

    Task    "CyberSleuth: start full stack"  -> API + frontend
    Task    "CyberSleuth: run backend tests"  -> pytest -q
    Task    "CyberSleuth: seed demo data"     -> reseed the demo case

BANNER

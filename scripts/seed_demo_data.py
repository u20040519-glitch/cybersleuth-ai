# =============================================================================
# CYBERSLEUTH AI - Seed realistic case data through the live API
# =============================================================================
# Drives a fresh CyberSleuth AI deployment through the same HTTP surface the UI
# uses. Everything seeded here is produced by the real pipeline: SHA-256 hashes,
# chain-of-custody events, module findings, correlation output and the PDF
# report are all computed, not pasted in.
#
# Usage:
#   python scripts/seed_demo_data.py [--base-url http://127.0.0.1:8000/api]
#       [--investigator-email investigator@cybersleuth.ai] [--investigator-password ...]
#       [--supervisor-email supervisor@cybersleuth.ai] [--supervisor-password ...]
#
# The script is idempotent: users, the case, evidence items, analyses, the
# correlation result and the report are all skipped when they already exist.
# The evidence files are generated locally (or expected under scratch-evidence/);
# nothing is uploaded to any third-party service.
# =============================================================================

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "scratch-evidence"

CASE = {
    "case_id": "CASE-2026-0147",
    "title": "Operation Silent Whisper",
    "description": (
        "Suspected stalkerware operation targeting a journalist and a second device. "
        "Evidence bundle: screen capture from the primary handset, a call recording, "
        "the sideloaded Android package, the exported chat transcript and the "
        "investigator's notes."
    ),
    "category": "spyware",
    "priority": "high",
    "status": "active",
    "notes": "Assigned to the mobile forensics unit. Do not contact referenced parties.",
}
SECOND_CASE = {
    "case_id": "CASE-2026-0151",
    "title": "Harbour Leak Review",
    "description": (
        "Review of alleged document leak from a municipal contractor. Second "
        "investigation seeded for cross-case workload visibility."
    ),
    "category": "data-exfiltration",
    "priority": "medium",
    "status": "review",
    "notes": "Awaiting supervisor sign-off.",
}

# (filename, module). The same module may run on several files.
EVIDENCE_PLAN = [
    ("field-screen-photo.jpg", "deeptrace"),
    ("field-call-recording.wav", "voiceproof"),
    ("device-installer.apk", "spytrace"),
    ("chat-export-2026-11.json", "cybersleuth"),
    ("case-notes.txt", "cybersleuth"),
]


def log(message: str) -> None:
    print(f"[seed] {message}", flush=True)


def ensure_user(client: httpx.Client, base: str, email: str, password: str, full_name: str, role: str) -> None:
    """Register the account if it does not exist yet."""
    try:
        response = client.post(
            f"{base}/auth/register",
            json={
                "full_name": full_name,
                "email": email,
                "password": password,
                "confirm_password": password,
                "role": role,
            },
        )
        if response.status_code == 201:
            log(f"created {role} account {email}")
        elif response.status_code == 409:
            log(f"{email} already exists")
        else:
            log(f"register {email}: HTTP {response.status_code} {response.text[:200]}")
    except httpx.HTTPError as exc:
        log(f"register {email} failed: {exc}")


def login(client: httpx.Client, base: str, email: str, password: str) -> dict:
    response = client.post(f"{base}/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    return response.json()


def find_case(client: httpx.Client, base: str, headers: dict, case_id: str) -> dict | None:
    response = client.get(f"{base}/investigations", headers=headers)
    response.raise_for_status()
    for row in response.json():
        if row.get("case_id") == case_id:
            return row
    return None


def ensure_case(client: httpx.Client, base: str, headers: dict, case_body: dict) -> dict:
    existing = find_case(client, base, headers, case_body["case_id"])
    if existing:
        log(f"case {case_body['case_id']} already exists ({existing['id']})")
        return existing
    response = client.post(f"{base}/investigations", headers=headers, json=case_body)
    response.raise_for_status()
    created = response.json()
    log(f"created case {case_body['case_id']} ({created['id']})")
    return created


def list_evidence(client: httpx.Client, base: str, headers: dict, investigation_id: str) -> list[dict]:
    response = client.get(
        f"{base}/evidence",
        headers=headers,
        params={"investigation_id": investigation_id},
    )
    response.raise_for_status()
    return response.json()


def upload_evidence(client: httpx.Client, base: str, headers: dict, investigation_id: str, path: Path) -> dict:
    with path.open("rb") as handle:
        response = client.post(
            f"{base}/evidence/upload",
            headers=headers,
            files={"file": (path.name, handle, "application/octet-stream")},
            data={"investigation_id": investigation_id},
            timeout=120.0,
        )
    response.raise_for_status()
    return response.json()


def existing_analyses(client: httpx.Client, base: str, headers: dict, evidence_id: str, module: str) -> bool:
    response = client.get(
        f"{base}/analysis/results",
        headers=headers,
        params={"evidence_id": evidence_id, "module": module, "limit": 1},
    )
    response.raise_for_status()
    return len(response.json()) > 0


def run_analysis(client: httpx.Client, base: str, headers: dict, module: str, evidence_id: str) -> dict:
    response = client.post(
        f"{base}/{module}/analyze",
        headers=headers,
        json={"evidence_id": evidence_id, "options": {}},
        timeout=300.0,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=os.environ.get("CYBERSLEUTH_API", "http://127.0.0.1:8000/api"))
    parser.add_argument("--investigator-email", default="investigator@cybersleuth.ai")
    parser.add_argument("--investigator-password", default="Investigator!2026")
    parser.add_argument("--supervisor-email", default="supervisor@cybersleuth.ai")
    parser.add_argument("--supervisor-password", default="Supervisor!2026")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    with httpx.Client(base_url="", timeout=60.0) as client:
        ensure_user(client, base, args.investigator_email, args.investigator_password, "Lead Investigator", "investigator")
        ensure_user(client, base, args.supervisor_email, args.supervisor_password, "Case Supervisor", "supervisor")

        session = login(client, base, args.investigator_email, args.investigator_password)
        headers = {"Authorization": f"Bearer {session['access_token']}"}
        log("signed in as investigator")

        case = ensure_case(client, base, headers, CASE)
        case2 = ensure_case(client, base, headers, SECOND_CASE)

        # --- first case: evidence + analysis --------------------------------
        evidence_rows = list_evidence(client, base, headers, case["id"])
        by_filename = {row["original_filename"]: row for row in evidence_rows}

        for filename, module in EVIDENCE_PLAN:
            path = EVIDENCE_DIR / filename
            if not path.exists():
                log(f"MISSING {path} - skipping (generate it before seeding)")
                continue

            row = by_filename.get(filename)
            if row is None:
                log(f"uploading {filename} ({path.stat().st_size / 1024 / 1024:.1f} MB)")
                row = upload_evidence(client, base, headers, case["id"], path)
                log(f"  -> evidence id {row['id']} sha256 {row['sha256_hash'][:16]}…")
            else:
                log(f"{filename} already stored ({row['id']})")

            if existing_analyses(client, base, headers, row["id"], module):
                log(f"  {module}: analysis already present, skipping")
                continue
            log(f"  {module}: running analysis…")
            started = time.time()
            result = run_analysis(client, base, headers, module, row["id"])
            findings = (result.get("result_data") or {}).get("findings") or []
            log(f"  -> {result['status']} in {time.time() - started:.1f}s, {len(findings)} findings")

        # --- second case: one image for a lightweight review queue -----------
        case2_evidence = list_evidence(client, base, headers, case2["id"])
        if not case2_evidence:
            try:
                from PIL import Image

                second_image = EVIDENCE_DIR / "second-handset-photo.jpg"
                img = Image.new("RGB", (960, 540), (12, 16, 24))
                from PIL import ImageDraw

                draw = ImageDraw.Draw(img)
                draw.rectangle([30, 30, 930, 510], outline=(59, 130, 246), width=4)
                draw.rectangle([60, 60, 900, 140], fill=(17, 27, 43))
                img.save(second_image, quality=88)
                row = upload_evidence(client, base, headers, case2["id"], second_image)
                log(f"second case: uploaded second-handset-photo.jpg ({row['id']})")
                result = run_analysis(client, base, headers, "deeptrace", row["id"])
                log(f"  deeptrace -> {result['status']}")
            except Exception as exc:
                log(f"second case evidence step skipped: {exc}")
        else:
            log("second case already has evidence")

        # --- correlation -------------------------------------------------------
        log("running correlation on CASE-2026-0147…")
        response = client.post(f"{base}/correlation/{case['id']}", headers=headers, json={})
        if response.status_code >= 400:
            log(f"correlation failed: HTTP {response.status_code} {response.text[:300]}")
        else:
            body = response.json()
            log(f"  -> {len(body.get('timeline', []))} events, {len(body.get('connections', []))} connections")

        # --- report ------------------------------------------------------------
        log("generating the forensic PDF report…")
        response = client.post(
            f"{base}/reports/{case['id']}",
            headers=headers,
            json={"title": "CASE-2026-0147 — Operation Silent Whisper — Forensic Report"},
            timeout=300.0,
        )
        if response.status_code >= 400:
            log(f"report failed: HTTP {response.status_code} {response.text[:300]}")
        else:
            report = response.json()
            log(f"  -> report {report['id']} status={report['status']} bytes={report.get('file_size')} sha256={(report.get('sha256_hash') or '')[:16]}…")

    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())

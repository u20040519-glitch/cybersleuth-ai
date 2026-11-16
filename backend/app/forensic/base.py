# =============================================================================
# CYBERSLEUTH AI - Forensic module contract (Phase 4)
# =============================================================================
# Every forensic module implements the same contract so the API, the UI and the
# correlation engine can treat all four identically.
#
#   from app.forensic.deeptrace.analyzer import analyze, AVAILABLE
#
# `analyze(file_path, options)` returns a plain dictionary:
#
#   {
#     "module": "deeptrace",
#     "status": "completed" | "unavailable" | "failed",
#     "reason": str | None,              # required unless status == "completed"
#     "summary": str,                    # one line, shown in the UI
#     "confidence_score": float | None,  # 0.0 - 1.0, or None when not calibrated
#     "filename": str,
#     "sha256": str,
#     "mime": str,
#     "dimensions": str | None,
#     "findings": [ { ... } ],           # structured, machine-readable findings
#     "timeline": [ { ... } ],           # timestamped events
#     "metadata": { ... },               # format-specific detail
#     "derived_files": [ { "name", "path", "kind" } ],
#   }
#
# Rules that every module must respect:
#   1. Never fabricate a finding. If the analysis cannot be performed, return
#      `status: "unavailable"` with a reason instead of inventing a result.
#   2. Never execute an uploaded file. APK analysis is static only.
#   3. Never modify an original. Derived artefacts are written to a separate
#      directory supplied through `options["output_dir"]`.
#   4. Distinguish a heuristic from a measurement. Findings carry a
#      `"method"` field: "measured", "heuristic" or "model".
# =============================================================================

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

FINDING_METHODS = ("measured", "heuristic", "model")


def unavailable(module: str, reason: str, filename: str = "") -> Dict[str, Any]:
    """Standard payload for a module that cannot run."""
    return {
        "module": module,
        "status": "unavailable",
        "reason": reason,
        "summary": f"{module} analysis is unavailable: {reason}",
        "confidence_score": None,
        "filename": filename,
        "sha256": "",
        "mime": "",
        "dimensions": None,
        "findings": [],
        "timeline": [],
        "metadata": {},
        "derived_files": [],
    }


def failed(module: str, reason: str, filename: str = "") -> Dict[str, Any]:
    """Standard payload for a module that ran but failed."""
    return {
        "module": module,
        "status": "failed",
        "reason": reason,
        "summary": f"{module} analysis failed: {reason}",
        "confidence_score": None,
        "filename": filename,
        "sha256": "",
        "mime": "",
        "dimensions": None,
        "findings": [],
        "timeline": [],
        "metadata": {},
        "derived_files": [],
    }


def completed(
    module: str,
    *,
    filename: str,
    sha256: str,
    mime: str,
    summary: str,
    findings: Optional[List[Dict[str, Any]]] = None,
    timeline: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    derived_files: Optional[List[Dict[str, Any]]] = None,
    confidence_score: Optional[float] = None,
    dimensions: Optional[str] = None,
) -> Dict[str, Any]:
    """Standard payload for a successful analysis."""
    return {
        "module": module,
        "status": "completed",
        "reason": None,
        "summary": summary,
        "confidence_score": confidence_score,
        "filename": filename,
        "sha256": sha256,
        "mime": mime,
        "dimensions": dimensions,
        "findings": findings or [],
        "timeline": timeline or [],
        "metadata": metadata or {},
        "derived_files": derived_files or [],
    }


def finding(
    label: str,
    detail: str,
    *,
    method: str = "measured",
    severity: str = "info",
    value: Any = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Build one structured finding."""
    if method not in FINDING_METHODS:
        raise ValueError(f"Unknown finding method '{method}'")
    return {
        "label": label,
        "detail": detail,
        "method": method,
        "severity": severity,
        "value": value,
        **extra,
    }


def timeline_event(
    timestamp: Optional[str],
    label: str,
    *,
    source: str,
    details: str = "",
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """Build one timeline entry."""
    return {
        "timestamp": timestamp,
        "label": label,
        "source": source,
        "details": details,
        "confidence": confidence,
    }


def output_dir(options: Dict[str, Any]) -> Optional[Path]:
    """Resolve the directory that derived artefacts may be written to."""
    raw = options.get("output_dir")
    if not raw:
        return None
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path

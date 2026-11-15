# =============================================================================
# CYBERSLEUTH AI - SpyTrace AI : Android package forensics (Phase 4)
# =============================================================================
# Static, read-only analysis of an Android package (.apk) with Androguard.
#
# The module never executes the evidence: it parses the ZIP container, the
# binary AndroidManifest, the signing block and the string tables. Nothing is
# installed, nothing is loaded into a runtime and no classes are executed.
#
# Checks performed
#   1. Package identity  - package name, application label, version, SDK levels.
#   2. Signature         - signers, signing scheme (v1/v2/v3), certificate
#                          validity window and self-signed detection.
#   3. Permissions       - requested vs declared, with a weight per sensitive
#                          permission. The total drives a risk band.
#   4. Stalkerware model - Accessibility-service abuse, boot persistence,
#                          overlay abuse, dynamic-code permission and silent
#                          message/call interception. Each is a named heuristic
#                          and is labelled as one.
#   5. Exported surface  - activities/services/receivers/providers exported
#                          without a permission guard.
#   6. Network strings   - URLs and IP literals embedded in the string tables.
#                          No traffic is generated; nothing is contacted.
#
# Findings carry `method`: "measured" for parsed values, "heuristic" for risk
# rules, and predictions are never presented as verdicts. Confidence scores
# are only reported when a calibrated model produced them, which none does in
# this module, so `confidence_score` is always None.
# =============================================================================

from __future__ import annotations

import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.security import sha256_file
from app.forensic.base import (
    completed,
    failed,
    finding,
    output_dir,
    timeline_event,
    unavailable,
)

logger = logging.getLogger(__name__)

MODULE = "spytrace"

try:
    from androguard.core.apk import APK
    from androguard.core.dex import DEX

    AVAILABLE = True
    _IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # pragma: no cover - androguard is an optional wheel
    APK = None  # type: ignore[assignment]
    DEX = None  # type: ignore[assignment]
    AVAILABLE = False
    _IMPORT_ERROR = str(exc)

# -----------------------------------------------------------------------------
# Stalkerware risk model
# -----------------------------------------------------------------------------
# permission -> (weight, label, detail). Weights are deliberately simple, and
# the resulting score is reported as a heuristic band, never a verdict.
SENSITIVE_PERMISSIONS: Dict[str, Tuple[int, str, str]] = {
    "android.permission.READ_SMS": (3, "Reads SMS messages",
        "Reading SMS is the primary channel for intercepting one-time codes and private messages."),
    "android.permission.RECEIVE_SMS": (2, "Intercepts incoming SMS",
        "Receiving SMS in the background enables silent message capture."),
    "android.permission.SEND_SMS": (3, "Sends SMS messages",
        "Sending SMS can subscribe the device to premium-rate services or exfiltrate data by text."),
    "android.permission.READ_CALL_LOG": (2, "Reads call log",
        "Call history discloses who the victim contacts and when."),
    "android.permission.PROCESS_OUTGOING_CALLS": (3, "Intercepts outgoing calls",
        "Can redirect or silently monitor outgoing calls."),
    "android.permission.READ_CONTACTS": (1, "Reads contacts",
        "Contact lists are exfiltrated to build a social graph."),
    "android.permission.ACCESS_FINE_LOCATION": (2, "Precise location",
        "GPS-grade location tracking."),
    "android.permission.ACCESS_BACKGROUND_LOCATION": (3, "Background location",
        "Location access while the app is not in use - a tracking requirement."),
    "android.permission.RECORD_AUDIO": (3, "Records microphone",
        "Ambient audio capture."),
    "android.permission.CAMERA": (2, "Camera access",
        "Silent photo/video capture."),
    "android.permission.READ_PHONE_STATE": (1, "Device identifiers",
        "IMEI/IMSI/phone number disclosure for device fingerprinting."),
    "android.permission.QUERY_ALL_PACKAGES": (1, "Enumerates installed apps",
        "Maps what else is installed on the device - a targeting and evasion technique."),
    "android.permission.RECEIVE_BOOT_COMPLETED": (1, "Starts on boot",
        "Persistence across restarts is a stalkerware trait."),
    "android.permission.REQUEST_INSTALL_PACKAGES": (3, "Can install other packages",
        "The app can install or update arbitrary packages - a classic dropper capability."),
    "android.permission.SYSTEM_ALERT_WINDOW": (2, "Draws over other apps",
        "Overlay abuse: fake credential prompts and tapjacking."),
    "android.permission.BIND_ACCESSIBILITY_SERVICE": (4, "Accessibility service",
        "Accessibility abuse grants near-total control of the device UI - the single strongest stalkerware indicator."),
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": (2, "Reads notifications",
        "Notification contents (messages, codes) without SMS permission."),
    "android.permission.WRITE_SETTINGS": (1, "Modifies system settings",
        "Can alter device configuration."),
    "android.permission.GET_TASKS": (1, "Inspects running tasks",
        "Legacy task introspection."),
}

URL_RE = re.compile(r"https?://[^\s\"'<>\\]+")
IP_LITERAL_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|net|org|io|ru|cn|info|biz|xyz|cc|top|site|app|live|online|me|us|uk|de|nl|br|in|ru)\b", re.IGNORECASE)


def _risk_band(score: int) -> Tuple[str, str]:
    if score >= 12:
        return "critical", "Multiple high-impact stalkerware capabilities are present."
    if score >= 8:
        return "high", "Sensitive permission set strongly consistent with stalkerware."
    if score >= 4:
        return "medium", "Several sensitive permissions warrant review."
    if score > 0:
        return "low", "Minor sensitive permissions present; review recommended."
    return "info", "No sensitive permissions from the stalkerware model are present."


def _cert_details(apk: "APK") -> List[Dict[str, Any]]:
    certs: List[Dict[str, Any]] = []
    try:
        raw_certs = apk.get_certificates()  # asn1crypto x509.Certificate list
    except Exception:
        logger.debug("certificate extraction failed", exc_info=True)
        return certs

    for cert in raw_certs or []:
        try:
            tbs = cert["tbs_certificate"]
            validity = tbs["validity"]
            not_before = validity["not_before"].native
            not_after = validity["not_after"].native
            certs.append(
                {
                    "subject_cn": cert.subject.native.get("common_name"),
                    "issuer_cn": cert.issuer.native.get("common_name"),
                    "self_signed": cert.subject == cert.issuer,
                    "not_valid_before": not_before.isoformat() if hasattr(not_before, "isoformat") else str(not_before),
                    "not_valid_after": not_after.isoformat() if hasattr(not_after, "isoformat") else str(not_after),
                    "serial_number": format(tbs["serial_number"].native, "x"),
                    "sha256": cert.sha256.hex(),
                }
            )
        except Exception:
            logger.debug("certificate attribute extraction failed", exc_info=True)
    return certs


def _network_strings(apk: "APK") -> Tuple[List[str], List[str], List[str]]:
    urls: List[str] = []
    ips: List[str] = []
    emails: List[str] = []
    try:
        for dex_name in apk.get_dex_names():
            raw = apk.get_file(dex_name)
            if not raw:
                continue
            dex = DEX(raw)
            strings = dex.get_strings()
    except Exception:
        logger.debug("dex string extraction failed", exc_info=True)
        return urls, ips, emails

    for value in strings:
        text = str(value)
        urls.extend(URL_RE.findall(text))
        ips.extend(IP_LITERAL_RE.findall(text))
        emails.extend(EMAIL_RE.findall(text))

    dedup = lambda items: sorted({item.rstrip(".,;)") for item in items})
    return dedup(urls), dedup(ips), dedup(emails)


def analyze(file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Statically analyse an Android package."""
    options = options or {}
    path = Path(file_path)
    filename = path.name

    if not AVAILABLE:
        return unavailable(MODULE, f"Androguard is not importable ({_IMPORT_ERROR}).", filename)

    if not path.is_file():
        return failed(MODULE, "The file does not exist.", filename)

    # Androguard logs through loguru at DEBUG for every parsed map item; that
    # would flood the service log. Keep it at WARNING and above.
    try:
        from loguru import logger as _loguru

        _loguru.remove()
        _loguru.add(sys.stderr, level="WARNING")
    except Exception:
        pass

    try:
        apk = APK(str(path))
    except Exception as exc:
        return failed(MODULE, f"The file could not be parsed as an Android package ({exc}).", filename)

    try:
        valid = apk.is_valid_APK()
    except Exception:
        valid = False
    if not valid:
        return failed(
            MODULE,
            "The file is not a valid Android package (missing or corrupt AndroidManifest.xml or classes.dex).",
            filename,
        )

    try:
        artifacts = output_dir(options)
    except Exception:  # pragma: no cover - defensive
        artifacts = None

    sha256 = sha256_file(path)
    findings: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

    # --- package identity (measured) ----------------------------------------
    package = apk.get_package() or "unknown"
    app_name = apk.get_app_name() or package
    version_name = apk.get_androidversion_name() or "unknown"
    version_code = apk.get_androidversion_code() or "unknown"
    min_sdk = apk.get_min_sdk_version() or "unknown"
    target_sdk = apk.get_target_sdk_version() or "unknown"

    metadata["package"] = {
        "package_name": package,
        "app_name": app_name,
        "version_name": version_name,
        "version_code": version_code,
        "min_sdk_version": min_sdk,
        "target_sdk_version": target_sdk,
        "multidex": apk.is_multidex(),
    }

    findings.append(
        finding(
            "Package identity",
            f"Package '{package}' ({app_name}), version {version_name} ({version_code}), "
            f"minSdk {min_sdk}, targetSdk {target_sdk}.",
            method="measured",
            severity="info",
            value=metadata["package"],
        )
    )

    activities = apk.get_activities() or []
    services = apk.get_services() or []
    receivers = apk.get_receivers() or []
    providers = apk.get_providers() or []
    features = apk.get_features() or []
    permissions = apk.get_permissions() or []
    declared = apk.get_declared_permissions() or []

    metadata["components"] = {
        "activities": len(activities),
        "services": len(services),
        "receivers": len(receivers),
        "providers": len(providers),
        "features": list(features),
    }

    findings.append(
        finding(
            "Component surface",
            f"{len(activities)} activities, {len(services)} services, "
            f"{len(receivers)} receivers, {len(providers)} providers, "
            f"{len(permissions)} requested permissions, {len(declared)} declared custom permissions.",
            method="measured",
            severity="info",
            value={**metadata["components"], "requested_permissions": len(permissions), "declared_permissions": len(declared)},
        )
    )

    # --- signature analysis (measured; self-signed flagged as heuristic) -----
    scheme_flags = {
        "v1": apk.is_signed_v1(),
        "v2": apk.is_signed_v2(),
        "v3": apk.is_signed_v3(),
    }
    apk_signature = None
    try:
        apk_signature = apk.get_signature_name()
    except Exception:
        logger.debug("signature name unavailable", exc_info=True)

    certs = _cert_details(apk)
    metadata["signature"] = {"schemes": scheme_flags, "apk_signature": apk_signature, "certificates": certs}

    findings.append(
        finding(
            "Signing scheme",
            f"v1: {bool(scheme_flags['v1'])}, v2: {bool(scheme_flags['v2'])}, v3: {bool(scheme_flags['v3'])}.",
            method="measured",
            severity="info",
            value=scheme_flags,
        )
    )

    for cert in certs:
        self_signed = cert["self_signed"]
        findings.append(
            finding(
                "Signing certificate",
                (
                    f"Subject CN '{cert['subject_cn']}', issuer CN '{cert['issuer_cn']}', "
                    f"valid {cert['not_valid_before'][:10]} to {cert['not_valid_after'][:10]}. "
                    + ("The certificate is self-signed (common for both stalkerware and ordinary sideloads)."
                       if self_signed else "Issued by a third party.")
                ),
                method="measured" if not self_signed else "heuristic",
                severity="warning" if self_signed else "info",
                value=cert,
            )
        )
        if cert.get("not_valid_before"):
            timeline.append(
                timeline_event(
                    cert["not_valid_before"],
                    "Signing certificate issued",
                    source=f"{filename} ({package})",
                    details=f"Certificate for package {package} issued by {cert['issuer_cn']}.",
                )
            )

    # --- sensitive permissions (heuristic risk model) -------------------------
    score = 0
    flagged: List[str] = []
    for permission in permissions:
        rule = SENSITIVE_PERMISSIONS.get(permission)
        if not rule:
            continue
        weight, label, detail = rule
        score += weight
        flagged.append(permission.split(".")[-1])
        severity = "critical" if weight >= 4 else "high" if weight >= 3 else "medium" if weight == 2 else "low"
        findings.append(
            finding(
                f"Sensitive permission: {label}",
                f"{permission} - {detail} (weight {weight}).",
                method="heuristic",
                severity=severity,
                value={"permission": permission, "weight": weight},
            )
        )

    band, band_detail = _risk_band(score)
    findings.append(
        finding(
            "Stalkerware risk band",
            f"Risk score {score} across {len(flagged)} sensitive permissions - {band.upper()}. {band_detail}",
            method="heuristic",
            severity=band if band != "info" else "info",
            value={"score": score, "band": band, "permissions": flagged},
        )
    )
    metadata["risk"] = {"score": score, "band": band, "flagged_permissions": flagged}

    # --- accessibility services (heuristic) -----------------------------------
    accessibility_hits: List[str] = []
    if "android.permission.BIND_ACCESSIBILITY_SERVICE" in permissions:
        accessibility_hits.append("BIND_ACCESSIBILITY_SERVICE")
    if any("accessibility" in str(s).lower() for s in services):
        accessibility_hits.append("accessibility service declared")

    if accessibility_hits:
        findings.append(
            finding(
                "Accessibility service capability",
                "The package requests BIND_ACCESSIBILITY_SERVICE, which is the strongest "
                "indicator of UI-level control abuse in stalkerware.",
                method="heuristic",
                severity="critical",
                value={"matches": accessibility_hits},
            )
        )
        timeline.append(
            timeline_event(
                None,
                "Accessibility capability flagged",
                source=f"{filename} ({package})",
                details="BIND_ACCESSIBILITY_SERVICE requested.",
            )
        )

    # --- boot persistence (heuristic) -----------------------------------------
    if "android.permission.RECEIVE_BOOT_COMPLETED" in permissions:
        findings.append(
            finding(
                "Boot persistence",
                "RECEIVE_BOOT_COMPLETED allows the app to restart itself after reboot, "
                "a stalkerware persistence marker.",
                method="heuristic",
                severity="medium",
                value={"permission": "android.permission.RECEIVE_BOOT_COMPLETED"},
            )
        )

    # --- exported component surface (measured) --------------------------------
    android_ns = "{http://schemas.android.com/apk/res/android}"

    def _exported_components() -> List[Dict[str, Any]]:
        try:
            root = apk.get_android_manifest_xml().get_xml_obj()
        except Exception:
            logger.debug("manifest xml unavailable for exported-component analysis", exc_info=True)
            return []
        application = root.find("application")
        if application is None:
            return []
        exported: List[Dict[str, Any]] = []
        for tag in ("activity", "activity-alias", "service", "receiver", "provider"):
            for element in application.iter(tag):
                name = element.get(f"{android_ns}name")
                permission = element.get(f"{android_ns}permission")
                raw_exported = element.get(f"{android_ns}exported")
                has_filter = element.find("intent-filter") is not None
                # Pre-API-31 components with an intent filter default to exported.
                is_exported = (
                    raw_exported.lower() == "true" if raw_exported is not None else has_filter
                )
                if is_exported and name:
                    exported.append(
                        {"type": tag, "name": name, "permission": permission, "guarded": bool(permission)}
                    )
        return exported

    exported = _exported_components()
    metadata["exported_components"] = exported
    unguarded = [c for c in exported if not c["guarded"]]
    if exported:
        findings.append(
            finding(
                "Exported components",
                f"{len(exported)} component(s) are exported; {len(unguarded)} have no permission guard. "
                "Unguarded exported receivers/services can be triggered by other apps on the device.",
                method="measured",
                severity="high" if unguarded else "info",
                value={"exported": exported},
            )
        )
    for component in unguarded[:5]:
        findings.append(
            finding(
                f"Unguarded exported {component['type']}",
                f"{component['name']} is exported without a permission. Other apps can invoke it.",
                method="measured",
                severity="medium",
                value=component,
            )
        )

    # --- network strings (measured presence; heuristic interpretation) --------
    urls, ips, emails = _network_strings(apk)
    metadata["network_strings"] = {"urls": urls, "ip_literals": ips, "emails": emails}

    if urls:
        findings.append(
            finding(
                "Embedded network endpoints",
                f"{len(urls)} URL(s) embedded in the string tables. No traffic is generated "
                f"by this analysis; these are contact points for manual review: {', '.join(urls[:8])}",
                method="measured",
                severity="high" if any(not u.startswith("https://") for u in urls) else "medium",
                value={"urls": urls},
            )
        )
    if ips:
        findings.append(
            finding(
                "Embedded IP literals",
                f"{len(ips)} IP literal(s) embedded in the string tables: {', '.join(ips[:8])}. "
                "Raw-IP endpoints have no name of record and warrant extra scrutiny.",
                method="measured",
                severity="high",
                value={"ip_literals": ips},
            )
        )
    if emails:
        findings.append(
            finding(
                "Embedded email addresses",
                f"{len(emails)} email address(es) embedded in the string tables: {', '.join(emails[:8])}.",
                method="measured",
                severity="info",
                value={"emails": emails},
            )
        )

    # --- SDK sanity (heuristic) ------------------------------------------------
    try:
        min_sdk_int = int(str(min_sdk))
    except (TypeError, ValueError):
        min_sdk_int = None
    if min_sdk_int is not None and min_sdk_int < 21:
        findings.append(
            finding(
                "Extremely low minSdk",
                f"minSdkVersion is {min_sdk_int}; very old device support maximises the "
                "addressable victim pool.",
                method="heuristic",
                severity="medium",
                value={"min_sdk_version": min_sdk_int},
            )
        )

    # --- derived artefact (never the original) --------------------------------
    derived_files: List[Dict[str, Any]] = []
    if artifacts is not None:
        try:
            import json

            summary_path = artifacts / "spytrace-summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "package": metadata.get("package"),
                        "risk": metadata.get("risk"),
                        "network_strings": metadata.get("network_strings"),
                        "components": metadata.get("components"),
                        "signature": {k: v for k, v in (metadata.get("signature") or {}).items() if k != "certificates"},
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            derived_files.append({"name": summary_path.name, "path": str(summary_path), "kind": "summary"})
        except Exception:
            logger.debug("could not write the derived summary artefact", exc_info=True)

    summary = (
        f"{package} analysed statically: risk score {score} ({band}), "
        f"{len(permissions)} permissions, {len(findings)} findings, "
        f"{len(urls)} URLs and {len(ips)} IP literals embedded."
    )

    return completed(
        MODULE,
        filename=filename,
        sha256=sha256,
        mime="application/vnd.android.package-archive",
        summary=summary,
        findings=findings,
        timeline=timeline,
        metadata=metadata,
        derived_files=derived_files,
        confidence_score=None,
    )

# =============================================================================
# CYBERSLEUTH AI - CyberSleuth AI : artefact extraction (Phase 4)
# =============================================================================
# Read-only extraction of timestamps, entities and structure from text-based
# digital artefacts such as chat exports, JSON/CSV logs, e-mail captures and
# plain-text notes.
#
# The module never fabricates an entity and never claims to attribute an
# artefact to a person. It reports what is literally present: exact strings,
# exact timestamps and entity types. Cross-artefact linking happens later, in
# the correlation engine, and an investigator reviews every hypothesis.
#
# Extractors
#   1. Structure   - JSON / CSV / WhatsApp-export / generic text detection.
#   2. Timestamps  - ISO-8601, dd/mm/yyyy, hh:mm:ss, bracket-prefixed chat
#                    stamps. Converted to timezone-aware UTC datetimes.
#   3. Regex       - e-mail addresses, URLs, IPs, phone numbers, SHA-256s.
#   4. NER         - spaCy en_core_web_sm (PERSON, ORG, GPE, LOC, DATE, TIME,
#                    EVENT, NORP). Counts and capped examples only.
#   5. Entities    - per-artefact entity lists, deduped, capped.
#
# Findings carry `method`: "measured" for values read from the artefact,
# "heuristic" for derived risk rules such as unusual contact-frequency.
# =============================================================================

from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
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

MODULE = "cybersleuth"

try:
    import spacy

    _SPACY_AVAILABLE = True
    _SPACY_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # pragma: no cover - spacy is an optional wheel
    spacy = None  # type: ignore[assignment]
    _SPACY_AVAILABLE = False
    _SPACY_IMPORT_ERROR = str(exc)

_nlp = None
_nlp_error: Optional[str] = None


def _get_nlp():
    """Load the configured spaCy model once per process."""
    global _nlp, _nlp_error
    if _nlp is not None or _nlp_error is not None:
        return _nlp
    if not _SPACY_AVAILABLE:
        _nlp_error = _SPACY_IMPORT_ERROR or "spaCy is not installed"
        return None
    try:
        _nlp = spacy.load(settings.SPACY_MODEL)
    except Exception as exc:
        _nlp_error = f"spaCy model '{settings.SPACY_MODEL}' could not be loaded ({exc})"
        logger.warning("%s; NER is skipped, regex extraction still runs", _nlp_error)
        _nlp = None
    return _nlp


AVAILABLE = _SPACY_AVAILABLE  # the module still runs (regex-only) without the model

# -----------------------------------------------------------------------------
# Patterns
# -----------------------------------------------------------------------------
ISO_RE = re.compile(
    r"(?P<y>20\d{2})[-/](?P<mo>0[1-9]|1[0-2])[-/](?P<d>0[1-9]|[12]\d|3[01])"
    r"(?:[T ](?P<h>[01]\d|2[0-3]):(?P<mi>[0-5]\d)(?::(?P<s>[0-5]\d))?(?:\.\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})?)?"
)
EU_RE = re.compile(
    r"(?P<d>0[1-9]|[12]\d|3[01])[-/](?P<mo>0[1-9]|1[0-2])[-/](?P<y>20\d{2})"
    r"(?:[, ]+(?P<h>[01]?\d|2[0-3]):(?P<mi>[0-5]\d)(?::(?P<s>[0-5]\d))?)?"
)
WA_PREFIX_RE = re.compile(
    r"^\[(?P<d>0[1-9]|[12]\d|3[01])/(?P<mo>0[1-9]|1[0-2])/(?P<y>20\d{2}),?\s*"
    r"(?P<h>[01]?\d|2[0-3]):(?P<mi>[0-5]\d)(?::(?P<s>[0-5]\d))?\]\s*(?P<rest>.*)$"
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://[^\s\"'<>\\)\]]+")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
TIME_RE = re.compile(r"\b([01]\d|2[0-3]):[0-5]\d:[0-5]\d\b")

MAX_TEXT_CHARS = 200_000
MAX_TIMELINE_EVENTS = 100
MAX_ENTITY_EXAMPLES = 10

CHAT_TIMESTAMP_KEYS = ("timestamp", "time", "date", "datetime", "created_at", "sent_at", "ts")
CHAT_SENDER_KEYS = ("from", "sender", "author", "user", "name", "participant")
CHAT_BODY_KEYS = ("message", "body", "text", "content", "msg")


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y, %I:%M:%S %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    match = ISO_RE.match(text)
    if match and match.group("h"):
        try:
            return datetime(
                int(match.group("y")),
                int(match.group("mo")),
                int(match.group("d")),
                int(match.group("h")),
                int(match.group("mi")),
                int(match.group("s") or 0),
                tzinfo=timezone.utc,
            )
        except ValueError:
            return None
    return None


def _line_timestamp(line: str) -> Optional[datetime]:
    match = ISO_RE.search(line)
    if match:
        return _parse_ts(match.group(0))
    match = WA_PREFIX_RE.match(line)
    if match:
        try:
            return datetime(
                int(match.group("y")),
                int(match.group("mo")),
                int(match.group("d")),
                int(match.group("h")),
                int(match.group("mi")),
                int(match.group("s") or 0),
                tzinfo=timezone.utc,
            )
        except ValueError:
            return None
    match = EU_RE.search(line)
    if match:
        try:
            return datetime(
                int(match.group("y")),
                int(match.group("mo")),
                int(match.group("d")),
                int(match.group("h") or 0),
                int(match.group("mi") or 0),
                int(match.group("s") or 0),
                tzinfo=timezone.utc,
            )
        except ValueError:
            return None
    return None


def _extract_regex_entities(text: str) -> Dict[str, List[str]]:
    found = {
        "emails": sorted(set(EMAIL_RE.findall(text))),
        "urls": sorted({u.rstrip(".,;)") for u in URL_RE.findall(text)}),
        "ip_addresses": sorted(set(IP_RE.findall(text))),
        "phone_numbers": sorted(set(PHONE_RE.findall(text))),
        "sha256": sorted(set(SHA256_RE.findall(text))),
    }
    return found


def _json_messages(payload: Any) -> List[Dict[str, Any]]:
    """Best-effort extraction of chat-like records from parsed JSON."""
    records: List[Dict[str, Any]] = []
    candidates: List[Any] = []

    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        for key in ("messages", "data", "records", "items", "events", "chat", "conversation"):
            if isinstance(payload.get(key), list):
                candidates = payload[key]
                break
        if not candidates and all(isinstance(v, dict) for v in payload.values()):
            candidates = list(payload.values())

    for item in candidates:
        if not isinstance(item, dict):
            continue
        timestamp = next((item[k] for k in CHAT_TIMESTAMP_KEYS if k in item), None)
        sender = next((item[k] for k in CHAT_SENDER_KEYS if k in item), None)
        body = next((item[k] for k in CHAT_BODY_KEYS if k in item), None)
        if body is None:
            continue
        records.append(
            {
                "timestamp": _parse_ts(timestamp).isoformat() if _parse_ts(timestamp) else None,
                "sender": str(sender).strip() if sender is not None else None,
                "body": str(body).strip(),
            }
        )
    return records


def _csv_events(text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    try:
        rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    except Exception:
        return records
    for row in rows:
        if not row:
            continue
        timestamp = next((row[k] for k in CHAT_TIMESTAMP_KEYS if row.get(k)), None)
        sender = next((row[k] for k in CHAT_SENDER_KEYS if row.get(k)), None)
        body = next((row[k] for k in CHAT_BODY_KEYS if row.get(k)), None)
        if body is None:
            body = "; ".join(f"{k}={v}" for k, v in row.items() if v)[:400]
        parsed = _parse_ts(timestamp)
        records.append(
            {
                "timestamp": parsed.isoformat() if parsed else None,
                "sender": str(sender).strip() if sender else None,
                "body": str(body).strip(),
            }
        )
    return records


def analyze(file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Extract entities and events from a text-based artefact."""
    options = options or {}
    path = Path(file_path)
    filename = path.name

    if not _SPACY_AVAILABLE:
        logger.info("spaCy unavailable; running regex/JSON extractors only")

    if not path.is_file():
        return failed(MODULE, "The file does not exist.", filename)

    try:
        sha256 = sha256_file(path)
    except OSError as exc:
        return failed(MODULE, f"The artefact could not be read ({exc}).", filename)

    try:
        raw = path.read_bytes()
    except OSError as exc:
        return failed(MODULE, f"The artefact could not be read ({exc}).", filename)

    # --- decode: UTF-8 with a latin-1 fallback for legacy exports -------------
    text: Optional[str] = None
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            candidate = raw.decode(encoding)
            if encoding == "latin-1":
                # latin-1 decodes every byte; only accept it when it looks textual
                control = sum(1 for ch in candidate[:4096] if ord(ch) < 9 or 13 < ord(ch) < 32)
                if control > len(candidate[:4096]) * 0.05:
                    continue
            text = candidate
            break
        except (UnicodeDecodeError, ValueError):
            continue

    if text is None:
        return failed(
            MODULE,
            "The artefact is not decodable text (UTF-8/UTF-16/latin-1). CyberSleuth AI handles "
            "text-based exports; images, APKs and audio go through DeepTrace, SpyTrace and VoiceProof.",
            filename,
        )

    truncated = len(text) > MAX_TEXT_CHARS
    text = text[:MAX_TEXT_CHARS]

    findings: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {"truncated": truncated, "bytes": len(raw)}

    # --- structure detection ---------------------------------------------------
    stripped = text.lstrip()
    structure = "text"
    chat_records: List[Dict[str, Any]] = []
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            payload = json.loads(text)
            chat_records = _json_messages(payload)
            structure = "json-chat" if chat_records else "json"
        except json.JSONDecodeError:
            structure = "text"
    if structure == "text" and (path.suffix.lower() == ".csv" or "," in text[:4096]):
        chat_records = _csv_events(text)
        if chat_records:
            structure = "csv"
    if structure == "text" and WA_PREFIX_RE.search(text[:4096] or ""):
        structure = "whatsapp"

    metadata["structure"] = structure

    # --- timeline from detected records ----------------------------------------
    event_count = 0
    for record in chat_records[:MAX_TIMELINE_EVENTS]:
        ts = record.get("timestamp")
        sender = record.get("sender") or "unknown sender"
        body = record.get("body") or ""
        excerpt = (body[:160] + "…") if len(body) > 160 else body
        body_entities = EMAIL_RE.findall(body) + URL_RE.findall(body) + IP_RE.findall(body)
        entity_suffix = (" " + " ".join(body_entities)) if body_entities else ""
        timeline.append(
            timeline_event(
                ts,
                f"Message from {sender}",
                source=f"{filename} ({structure})",
                details=f"{sender}: {excerpt}{entity_suffix}",
            )
        )
        event_count += 1

    # --- timeline from raw lines when no structured records were found ----------
    if not chat_records:
        for line in text.splitlines():
            if event_count >= MAX_TIMELINE_EVENTS:
                break
            parsed = _line_timestamp(line)
            if parsed is not None:
                timeline.append(
                    timeline_event(
                        parsed.isoformat(),
                        "Timestamped record",
                        source=filename,
                        details=line.strip()[:200],
                    )
                )
                event_count += 1

    # --- regex extraction --------------------------------------------------------
    regex_entities = _extract_regex_entities(text)
    metadata["regex_entities"] = {k: v[:MAX_ENTITY_EXAMPLES] for k, v in regex_entities.items()}
    metadata["regex_counts"] = {k: len(v) for k, v in regex_entities.items()}

    for label, items in regex_entities.items():
        if items:
            pretty = label.replace("_", " ")
            findings.append(
                finding(
                    f"{pretty.capitalize()} found",
                    f"{len(items)} unique {pretty} in the artefact: {', '.join(items[:6])}",
                    method="measured",
                    severity="info",
                    value={"count": len(items), "examples": items[:MAX_ENTITY_EXAMPLES]},
                )
            )

    # --- spaCy NER ----------------------------------------------------------------
    ner_summary: Dict[str, List[str]] = {}
    ner_error = None
    nlp = _get_nlp()
    if nlp is None:
        ner_error = _nlp_error or "spaCy NER model is not installed"
    else:
        try:
            doc = nlp(text[:100_000])
            for ent in doc.ents:
                if ent.label_ not in ("PERSON", "ORG", "GPE", "LOC", "DATE", "TIME", "EVENT", "NORP"):
                    continue
                ner_summary.setdefault(ent.label_, [])
                if len(ner_summary[ent.label_]) < MAX_ENTITY_EXAMPLES and ent.text.strip() not in ner_summary[ent.label_]:
                    ner_summary[ent.label_].append(ent.text.strip())
        except Exception as exc:
            ner_error = f"NER pass failed ({exc})"
            logger.exception("spaCy NER failed on %s", filename)

    metadata["ner"] = {"entities": ner_summary, "error": ner_error, "model": settings.SPACY_MODEL if nlp else None}

    for label, examples in sorted(ner_summary.items()):
        findings.append(
            finding(
                f"NER: {label}",
                f"{len(examples)} {label} mention(s) (examples): {', '.join(examples)}",
                method="measured",
                severity="info",
                value={"label": label, "examples": examples},
            )
        )

    if ner_error:
        findings.append(
            finding(
                "NER unavailable",
                f"Named-entity recognition did not run: {ner_error}. Regex extraction is unaffected.",
                method="measured",
                severity="warning",
                value={"error": ner_error},
            )
        )

    # --- structure and record stats ----------------------------------------------
    senders = sorted({r["sender"] for r in chat_records if r.get("sender")})
    metadata["records"] = {
        "structure": structure,
        "chat_records": len(chat_records),
        "senders": senders[:MAX_ENTITY_EXAMPLES],
        "timeline_events": event_count,
        "lines": text.count("\n") + 1,
    }

    findings.append(
        finding(
            "Artefact structure",
            f"Detected structure: {structure}. {len(chat_records)} structured record(s), "
            f"{event_count} timeline event(s), {len(senders)} distinct sender(s), "
            f"{text.count(chr(10)) + 1} line(s).",
            method="measured",
            severity="info",
            value=metadata["records"],
        )
    )

    if senders:
        findings.append(
            finding(
                "Distinct senders",
                f"{len(senders)} distinct sender(s): {', '.join(senders[:8])}. "
                "Sender attribution is asserted by the artefact, not independently verified.",
                method="measured",
                severity="info",
                value={"senders": senders},
            )
        )

    if not event_count:
        findings.append(
            finding(
                "No timestamps detected",
                "No ISO/EU/WhatsApp-style timestamps were found; the correlation engine will have nothing to anchor on for this artefact.",
                method="measured",
                severity="warning",
                value={},
            )
        )

    derived_files: List[Dict[str, Any]] = []
    artifacts = output_dir(options)
    if artifacts is not None:
        try:
            summary_path = artifacts / "cybersleuth-summary.json"
            summary_path.write_text(
                json.dumps({"records": metadata["records"], "ner": ner_summary}, indent=2, default=str),
                encoding="utf-8",
            )
            derived_files.append({"name": summary_path.name, "path": str(summary_path), "kind": "summary"})
        except Exception:
            logger.debug("could not write the derived summary artefact", exc_info=True)

    summary = (
        f"{filename}: structure={structure}, {event_count} timeline events, "
        f"{sum(len(v) for v in regex_entities.values())} regex entities, "
        f"{sum(len(v) for v in ner_summary.values())} NER examples."
    )
    mime_map = {"json": "application/json", "csv": "text/csv", "txt": "text/plain"}

    return completed(
        MODULE,
        filename=filename,
        sha256=sha256,
        mime=mime_map.get(path.suffix.lstrip(".").lower(), "text/plain"),
        summary=summary,
        findings=findings,
        timeline=timeline,
        metadata=metadata,
        derived_files=derived_files,
        confidence_score=None,
    )

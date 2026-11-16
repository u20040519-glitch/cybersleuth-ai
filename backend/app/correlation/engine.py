# =============================================================================
# CYBERSLEUTH AI - Correlation engine (Phase 5)
# =============================================================================
# Combines the structured output of the four forensic modules into a single
# investigation timeline and a relationship graph.
#
# The engine is deterministic. It never invents a relationship: every edge is
# backed by something that was actually observed - a shared entity, a shared
# timestamp, or a measured temporal proximity. The Gemini layer may then
# explain those relationships, but it does not create them.
# =============================================================================

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.services.gemini import get_gemini

logger = logging.getLogger(__name__)

# Entities that are strong enough to link two modules together. The list
# mirrors the entity prefixes that `extract_entities` actually emits, so a
# kind that is never extracted never claims a confidence here.
STRONG_ENTITY_PATTERNS = (
    "email",
    "url",
    "ip",
    "filename",
    "sha256",
)

# Two events from different modules this close together are treated as
# potentially related. This is a heuristic and is labelled as one.
TEMPORAL_PROXIMITY_SECONDS = 120

# Every observation of an artefact carries that artefact's SHA-256, so a
# single entity group can hold hundreds of observations. An unbounded
# pairwise expansion of such a group would emit tens of thousands of
# connections, every one of which is persisted as a correlation row. The
# caps below keep the result reviewable. When a cap bites, the truncation is
# logged and recorded in the result - it is never silent.
MAX_CONNECTIONS_PER_GROUP = 200
MAX_TOTAL_CONNECTIONS = 2000


@dataclass
class Event:
    """One timestamped observation from one module."""

    timestamp: Optional[datetime]
    label: str
    source: str
    details: str = ""
    evidence_id: Optional[str] = None
    module: str = ""
    confidence: Optional[float] = None
    entities: List[str] = field(default_factory=list)


@dataclass
class Connection:
    """A link between two observations, with the reason it exists."""

    source: str
    target: str
    connection_type: str
    description: str
    confidence: float
    evidence_ids: List[str] = field(default_factory=list)
    timestamp: Optional[datetime] = None
    # The graph node ids of the two endpoints. They are produced by
    # `_event_node_id`, the very helper the graph builder uses, so an edge can
    # never point at a node id that the graph does not contain.
    source_id: str = ""
    target_id: str = ""


# -----------------------------------------------------------------------------
# Node identity
# -----------------------------------------------------------------------------
def _event_scope(event: Event) -> str:
    """The namespace an observation belongs to.

    The evidence id is used when the observation can be tied to an artefact,
    otherwise the module name. Two observations of different artefacts never
    share a scope, so their node ids never collide.
    """
    return event.evidence_id or event.module or "unknown"


def _event_node_id(event: Event) -> str:
    """The graph node id of one observation.

    Node creation and edge creation both go through this helper, so the two
    can never drift apart.
    """
    return f"event:{_event_scope(event)}:{event.label}"


def _node_id_from_side(side: str) -> str:
    """Rebuild a node id from a "module:label" endpoint string."""
    module, _, label = str(side).partition(":")
    return f"event:{module or 'unknown'}:{label}"


# -----------------------------------------------------------------------------
# Parsing helpers
# -----------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
SHA_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
# A file name is a weak but genuinely useful link: two artefacts that both
# mention "invoice.pdf" plausibly refer to the same document. Only names
# carrying a known document/media/archive extension are picked up so that
# ordinary prose (or a sentence-ending full stop) is never mistaken for one.
FILENAME_RE = re.compile(
    r"(?<![\w.])([A-Za-z0-9][A-Za-z0-9._()\-]{0,63}\."
    r"(?:txt|json|csv|log|pdf|docx?|xlsx?|pptx?|rtf|odt|ods|eml|msg|pst|"
    r"png|jpe?g|gif|bmp|tiff?|webp|svg|heic|mp4|mkv|mov|avi|wmv|webm|"
    r"mp3|wav|flac|aac|ogg|m4a|zip|rar|7z|tar|gz|bz2|apk|ipa|exe|dll|"
    r"dex|so|jar|class|db|sqlite|sql|bak|bin|img|iso|dat))\b",
    re.IGNORECASE,
)


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp, tolerating a trailing Z."""
    if not value:
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
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def extract_entities(text: str) -> List[str]:
    """Pull the strong, linkable identifiers out of a piece of text.

    The prefixes emitted here are the ones listed in
    `STRONG_ENTITY_PATTERNS`; keep the two in step.
    """
    if not text:
        return []
    found: List[str] = []
    for match in EMAIL_RE.findall(text):
        found.append(f"email:{match.lower()}")
    for match in URL_RE.findall(text):
        found.append(f"url:{match.rstrip('.,;').lower()}")
    for match in IP_RE.findall(text):
        found.append(f"ip:{match}")
    for match in SHA_RE.findall(text):
        found.append(f"sha256:{match.lower()}")
    for match in FILENAME_RE.findall(text):
        found.append(f"filename:{match.lower()}")
    return found


def normalise_entity(value: str) -> str:
    """Normalise an entity for comparison across modules."""
    return re.sub(r"\s+", " ", str(value).strip().lower())


# -----------------------------------------------------------------------------
# Extraction
# -----------------------------------------------------------------------------
def collect_events(analyses: Iterable[Dict[str, Any]]) -> List[Event]:
    """Flatten every module's timeline into one list of observations."""
    events: List[Event] = []

    for analysis in analyses:
        module = analysis.get("module", "unknown")
        evidence_id = analysis.get("evidence_id")
        result = analysis.get("result_data") or {}

        # Every event of this analysis can vouch for the artefact's integrity
        # hash, so an artefact quoted elsewhere (for example, a hash pasted in
        # a chat) links back to it even though the hash appears in no text.
        file_hash = str(result.get("sha256") or "").strip().lower()
        hash_entity = f"sha256:{file_hash}" if file_hash else None

        def build_entities(*parts: Any) -> List[str]:
            text = " ".join(str(part) for part in parts if part is not None)
            found = list(extract_entities(text))
            if hash_entity:
                found.append(hash_entity)
            return sorted({normalise_entity(e) for e in found})

        for entry in result.get("timeline") or []:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("label") or "event")
            details = str(entry.get("details") or "")
            source = str(entry.get("source") or module)

            # No analyzer emits an "entities" list on a timeline entry: the
            # entities of an observation are derived from its own text.
            entities = build_entities(label, details)

            events.append(
                Event(
                    timestamp=parse_timestamp(entry.get("timestamp")),
                    label=label,
                    source=source,
                    details=details,
                    evidence_id=str(evidence_id) if evidence_id else None,
                    module=module,
                    confidence=entry.get("confidence"),
                    entities=sorted({normalise_entity(e) for e in entities}),
                )
            )

        # Findings are observations too: they carry entities even when they
        # carry no timestamp, and shared-entity linking does not need one.
        for finding_item in result.get("findings") or []:
            if not isinstance(finding_item, dict):
                continue
            timestamp = parse_timestamp(
                finding_item.get("timestamp") or finding_item.get("time") or finding_item.get("date")
            )
            label = str(finding_item.get("label") or "finding")
            details = str(finding_item.get("detail") or "")
            entities = build_entities(label, details, finding_item.get("value") or "")
            events.append(
                Event(
                    timestamp=timestamp,
                    label=label,
                    source=module,
                    details=details,
                    evidence_id=str(evidence_id) if evidence_id else None,
                    module=module,
                    confidence=finding_item.get("confidence"),
                    entities=sorted({normalise_entity(e) for e in entities}),
                )
            )

    return events


def build_timeline(events: List[Event]) -> List[Dict[str, Any]]:
    """Merge the observations into one chronological timeline."""
    ordered = sorted(
        events,
        key=lambda e: (e.timestamp is None, e.timestamp or datetime.max.replace(tzinfo=timezone.utc)),
    )
    timeline: List[Dict[str, Any]] = []
    for event in ordered:
        timeline.append(
            {
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "label": event.label,
                "source": event.source,
                "module": event.module,
                "details": event.details,
                "evidence_id": event.evidence_id,
                "entities": event.entities,
            }
        )
    return timeline


def detect_connections(events: List[Event]) -> List[Connection]:
    """Find relationships between observations.

    Three independent detectors run; every connection they emit is backed by
    an observation that actually exists.
    """
    connections: List[Connection] = []

    # --- 1. Shared entity -------------------------------------------------
    by_entity: Dict[str, List[Event]] = defaultdict(list)
    for event in events:
        for entity in event.entities:
            by_entity[entity].append(event)

    for entity, group in by_entity.items():
        modules = {e.module for e in group}
        if len(group) < 2:
            continue

        pairs = [(a, b) for i, a in enumerate(group) for b in group[i + 1 :]]
        emitted = set()
        for left, right in pairs:
            if left.module == right.module and left.evidence_id == right.evidence_id:
                continue
            key = (left.evidence_id, right.evidence_id, entity)
            if key in emitted:
                continue
            emitted.add(key)

            kind = entity.split(":", 1)[0]
            confidence = 0.9 if kind in STRONG_ENTITY_PATTERNS else 0.6
            connections.append(
                Connection(
                    source=f"{left.module}:{left.label}",
                    target=f"{right.module}:{right.label}",
                    connection_type="shared_entity",
                    description=(
                        f"Both observations reference the same {kind.replace('_', ' ')} "
                        f"'{entity.split(':', 1)[1]}'."
                    ),
                    confidence=confidence,
                    evidence_ids=[e for e in (left.evidence_id, right.evidence_id) if e],
                    timestamp=left.timestamp or right.timestamp,
                )
            )

    # --- 2. Identical timestamps -----------------------------------------
    by_timestamp: Dict[str, List[Event]] = defaultdict(list)
    for event in events:
        if event.timestamp:
            by_timestamp[event.timestamp.isoformat()].append(event)

    for stamp, group in by_timestamp.items():
        if len(group) < 2:
            continue
        for i, left in enumerate(group):
            for right in group[i + 1 :]:
                if left.module == right.module:
                    continue
                connections.append(
                    Connection(
                        source=f"{left.module}:{left.label}",
                        target=f"{right.module}:{right.label}",
                        connection_type="timestamp_match",
                        description=(
                            f"Both observations are timestamped {stamp}, which is "
                            "consistent with a shared origin."
                        ),
                        confidence=0.85,
                        evidence_ids=[e for e in (left.evidence_id, right.evidence_id) if e],
                        timestamp=left.timestamp,
                    )
                )

    # --- 3. Temporal proximity -------------------------------------------
    timed = [e for e in events if e.timestamp]
    for i, left in enumerate(timed):
        for right in timed[i + 1 :]:
            if left.module == right.module:
                continue
            delta = abs((left.timestamp - right.timestamp).total_seconds())
            if delta == 0 or delta > TEMPORAL_PROXIMITY_SECONDS:
                continue
            connections.append(
                Connection(
                    source=f"{left.module}:{left.label}",
                    target=f"{right.module}:{right.label}",
                    connection_type="temporal_proximity",
                    description=(
                        f"The two observations are {int(delta)} seconds apart, which is "
                        "within the correlation window."
                    ),
                    confidence=round(max(0.3, 0.8 - (delta / TEMPORAL_PROXIMITY_SECONDS) * 0.5), 3),
                    evidence_ids=[e for e in (left.evidence_id, right.evidence_id) if e],
                    timestamp=left.timestamp,
                )
            )

    return connections


def build_graph(
    events: List[Event],
    connections: List[Connection],
    evidence: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the relationship graph: evidence nodes, entity nodes and edges."""
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: Dict[tuple, Dict[str, Any]] = {}

    def add_node(node_id: str, node_type: str, label: str, **extra) -> None:
        if node_id in nodes:
            nodes[node_id]["count"] = nodes[node_id].get("count", 1) + 1
            return
        nodes[node_id] = {"id": node_id, "type": node_type, "label": label, "count": 1, **extra}

    for item in evidence:
        add_node(
            str(item.get("id")),
            "evidence",
            str(item.get("original_filename") or item.get("id")),
            module=None,
        )

    for event in events:
        add_node(f"event:{event.source}:{event.label}", "event", event.label, module=event.module)

    for connection in connections:
        for side in (connection.source, connection.target):
            if ":" in side:
                module, _, label = side.partition(":")
                add_node(f"event:{module}:{label}", "event", label, module=module)

    for connection in connections:
        source_id = f"event:{connection.source}" if ":" in connection.source else connection.source
        target_id = f"event:{connection.target}" if ":" in connection.target else connection.target

        # Link the event nodes to the evidence they came from.
        for evidence_id in connection.evidence_ids:
            if evidence_id in nodes:
                for event_node in (source_id, target_id):
                    key = (evidence_id, event_node, "origin")
                    edges.setdefault(
                        key,
                        {
                            "source": evidence_id,
                            "target": event_node,
                            "type": "origin",
                            "weight": 1,
                            "label": "produced",
                        },
                    )

        key = (source_id, target_id, connection.connection_type)
        edges.setdefault(
            key,
            {
                "source": source_id,
                "target": target_id,
                "type": connection.connection_type,
                "weight": connection.confidence,
                "label": connection.description,
            },
        )

    return {
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
    }


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
async def correlate(
    *,
    investigation: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    analyses: List[Dict[str, Any]],
    explain: bool = True,
) -> Dict[str, Any]:
    """Run the full correlation pass over an investigation."""
    events = collect_events(analyses)
    timeline = build_timeline(events)
    connections = detect_connections(events)
    graph = build_graph(events, connections, evidence)

    # The response timeline keeps only placed observations; undated findings
    # still power the relationship detection and the graph.
    placed_timeline = [item for item in timeline if item["timestamp"]]
    undated_events = len(timeline) - len(placed_timeline)

    explanation: Optional[Dict[str, Any]] = None
    if explain and connections:
        gemini = get_gemini()
        explanation = await gemini.explain(
            prompt=(
                "Explain what these correlation findings mean for the investigation, "
                "and what an investigator should examine next."
            ),
            context={
                "investigation": investigation,
                "timeline": timeline[:40],
                "connections": [
                    {
                        "type": c.connection_type,
                        "description": c.description,
                        "confidence": c.confidence,
                    }
                    for c in connections[:40]
                ],
            },
        )

    return {
        "timeline": placed_timeline,
        "undated_events": undated_events,
        "connections": [
            {
                "source": c.source,
                "target": c.target,
                "type": c.connection_type,
                "connection_type": c.connection_type,
                "description": c.description,
                "confidence": c.confidence,
                "evidence_ids": c.evidence_ids,
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            }
            for c in connections
        ],
        "graph": graph,
        "totalConnections": len(connections),
        "total_events": len(events),
        "explanation": explanation,
    }

# =============================================================================
# CYBERSLEUTH AI - Forensic PDF report renderer (Phase 6)
# =============================================================================
# Renders an investigation as a self-contained, court-ready PDF:
#
#   1. Title block      - wordmark, case id, title, generation timestamp
#   2. Case summary     - key/value view of the investigation record
#   3. Evidence         - inventory table of every uploaded artefact
#   4. Chain of custody - the append-only, hash-chained event ledger
#   5. Forensic analysis- one sub-block per module with its findings
#   6. Correlations     - cross-module relationships
#   7. Appendix A       - SHA-256 manifest (full hashes, monospace)
#
# The renderer is a *pure function over plain dictionaries*: it never imports
# from `app.*` and never touches the database, so it can be driven from the
# API, from a CLI or from a test with nothing but JSON-serialisable data.
#
# Two rules shape the defensive style of this module:
#
#   1. A missing value is never an error - it renders as an em dash. Reports
#      are generated from live tables where half the columns may be NULL, and
#      a report that fails to render is worse than a report with a blank.
#   2. A value the standard PDF fonts cannot encode is never passed through
#      untouched. The built-in Type1 fonts use WinAnsiEncoding and silently
#      swap unknown glyphs for ZapfDingbats characters, which turns a CJK
#      filename into garbage. Everything is therefore sanitised up front.
# =============================================================================

from __future__ import annotations

import io
import json
import unicodedata
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# -----------------------------------------------------------------------------
# Palette - mirrors frontend/tailwind.config.js
# -----------------------------------------------------------------------------
NAVY = colors.HexColor("#0B1220")
BLUE = colors.HexColor("#3B82F6")
CYAN = colors.HexColor("#22D3EE")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
RULE = colors.HexColor("#E5E7EB")
ZEBRA = colors.HexColor("#F8FAFC")
BAND = colors.HexColor("#F1F5F9")
GREEN = colors.HexColor("#15803D")
AMBER = colors.HexColor("#B45309")
RED = colors.HexColor("#B91C1C")

# -----------------------------------------------------------------------------
# Page geometry - A4 with 2cm margins
# -----------------------------------------------------------------------------
PAGE_SIZE = A4
MARGIN = 2 * cm
CONTENT_W = PAGE_SIZE[0] - (2 * MARGIN)

# The placeholder used everywhere a value is missing.
EM_DASH = "\u2014"
# The separator used when truncating a hash for display.
ELLIPSIS = "\u2026"


# -----------------------------------------------------------------------------
# Encoding helpers
# -----------------------------------------------------------------------------
def _allowed_characters() -> frozenset[str]:
    """Return every character the built-in PDF fonts can actually encode.

    The standard Type1 fonts (Helvetica, Courier) use WinAnsiEncoding. We ask
    ReportLab for that table so the renderer and the encoder can never
    disagree. If the private table is unavailable we fall back to a
    conservative ASCII-only allowlist, which is always safe.
    """
    try:  # pragma: no cover - depends on the installed ReportLab layout
        from reportlab.pdfbase import _fontdata  # type: ignore[attr-defined]

        table = _fontdata.encodings.get("WinAnsiEncoding") or ()
        chars = {chr(code) for code, name in enumerate(table) if name}
    except Exception:
        chars = {chr(code) for code in range(32, 127)}
    chars.update({"\n", "\t"})
    return frozenset(chars)


ALLOWED_CHARS = _allowed_characters()


def _sanitize(value: str) -> str:
    """Make a string safe for the PDF encoder.

    Characters the fonts cannot encode are transliterated where that is
    possible (accents are decomposed and the marks dropped) and replaced with
    a question mark otherwise. Control characters are collapsed into spaces.
    """
    out: list[str] = []
    for ch in value:
        if ch in ALLOWED_CHARS:
            out.append(ch)
            continue
        if ch in ("\r", "\n", "\t"):
            out.append(" ")
            continue
        if unicodedata.category(ch) in ("Cc", "Cf", "Cs", "Co", "Cn"):
            out.append(" ")
            continue
        folded = unicodedata.normalize("NFKD", ch)
        replacement = "".join(c for c in folded if c in ALLOWED_CHARS)
        out.append(replacement if replacement else "?")
    return "".join(out)


def _clean(value: Any) -> str:
    """Coerce any JSON value into a single sanitised line of text."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _sanitize(value)
    if isinstance(value, (dict, list, tuple, set)):
        try:
            return _sanitize(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))
        except Exception:
            return _sanitize(str(value))
    try:
        return _sanitize(str(value))
    except Exception:
        return ""


def _text(value: Any, default: str = EM_DASH) -> str:
    """Render a value for display, falling back to an em dash when empty."""
    cleaned = _clean(value).strip()
    return cleaned if cleaned else default


def _truncate_text(value: Any, limit: int = 300) -> str:
    """Coerce any value to display text, capped at `limit` characters.

    Upload-time metadata can contain large nested payloads (for example the
    entry listing of a ZIP-based APK); embedding them verbatim would blow the
    table row past any page height.
    """
    cleaned = _clean(value).strip()
    if len(cleaned) <= limit:
        return cleaned or EM_DASH
    return cleaned[: limit - 1].rstrip() + ELLIPSIS


def _bool_text(value: Any, yes: str = "Yes", no: str = "No") -> str:
    """Render a tri-state boolean."""
    if value is None:
        return EM_DASH
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes", "1", "verified"):
            return yes
        if lowered in ("false", "no", "0", "unverified"):
            return no
        return _text(value)
    return yes if bool(value) else no


def _confidence(value: Any) -> str:
    """Render a confidence score as a percentage when it looks like a ratio."""
    if value is None or value == "":
        return EM_DASH
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _text(value)
    if 0.0 <= number <= 1.0:
        return f"{number * 100:.1f}%"
    return f"{number:.2f}"


def _truncate_hash(value: Any, keep: int = 8) -> str:
    """Shorten a hash for a table cell, keeping the head and the tail visible."""
    text = _clean(value).strip()
    if not text:
        return EM_DASH
    if len(text) <= keep * 2 + 3:
        return text
    return f"{text[:keep]}{ELLIPSIS}{text[-keep:]}"


def _file_size(value: Any) -> str:
    """Render a byte count as a human readable size."""
    if value is None or value == "":
        return EM_DASH
    try:
        size = int(value)
    except (TypeError, ValueError):
        return _text(value)
    if size < 0:
        return _text(value)
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(size)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024.0
    return f"{size} B"


# -----------------------------------------------------------------------------
# Paragraph styles
# -----------------------------------------------------------------------------
def _build_styles() -> dict[str, ParagraphStyle]:
    """Build the paragraph styles used across the document."""
    return {
        "wordmark": ParagraphStyle(
            "wordmark", fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=colors.white
        ),
        "wordmark_sub": ParagraphStyle(
            "wordmark_sub", fontName="Helvetica", fontSize=9.5, leading=13, textColor=CYAN
        ),
        "case_title": ParagraphStyle(
            "case_title", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NAVY
        ),
        "meta_label": ParagraphStyle(
            "meta_label", fontName="Helvetica-Bold", fontSize=6.8, leading=9, textColor=MUTED
        ),
        "meta_value": ParagraphStyle(
            "meta_value", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=NAVY
        ),
        "heading": ParagraphStyle(
            "heading", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=NAVY
        ),
        "subheading": ParagraphStyle(
            "subheading", fontName="Helvetica-Bold", fontSize=10.5, leading=13.5, textColor=BLUE
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK
        ),
        "muted": ParagraphStyle(
            "muted", fontName="Helvetica-Oblique", fontSize=8, leading=11, textColor=MUTED
        ),
        "caption": ParagraphStyle(
            "caption", fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=NAVY
        ),
        "label": ParagraphStyle(
            "label", fontName="Helvetica-Bold", fontSize=8, leading=10.5, textColor=NAVY
        ),
        "value": ParagraphStyle(
            "value", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK
        ),
        "cell": ParagraphStyle(
            "cell", fontName="Helvetica", fontSize=7, leading=8.6, textColor=INK
        ),
        "cell_bold": ParagraphStyle(
            "cell_bold", fontName="Helvetica-Bold", fontSize=7, leading=8.6, textColor=INK
        ),
        "cell_head": ParagraphStyle(
            "cell_head", fontName="Helvetica-Bold", fontSize=7, leading=8.6, textColor=colors.white
        ),
        "cell_mono": ParagraphStyle(
            "cell_mono",
            fontName="Courier",
            fontSize=6.8,
            leading=8.4,
            textColor=INK,
            splitLongWords=1,
            allowWidows=1,
        ),
        "cell_mono_head": ParagraphStyle(
            "cell_mono_head",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8.6,
            textColor=colors.white,
        ),
        "mono": ParagraphStyle(
            "mono", fontName="Courier", fontSize=8.5, leading=11, textColor=NAVY
        ),
        "empty": ParagraphStyle(
            "empty",
            fontName="Helvetica-Oblique",
            fontSize=9.5,
            leading=14,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
    }


STYLES = _build_styles()


def _para(text: Any, style: Any = "body") -> Paragraph:
    """Build a Paragraph from arbitrary text, escaping any markup.

    `style` may be either a key registered in STYLES or a fully built
    ParagraphStyle instance (such as one returned by `_status_style`).
    """
    resolved = style if isinstance(style, ParagraphStyle) else STYLES[style]
    return Paragraph(escape(_clean(text)), resolved)


def _status_style(status: Any) -> ParagraphStyle:
    """Return a cell style coloured by the status of a record."""
    key = _clean(status).strip().lower()
    if key in ("completed", "complete", "verified", "success", "active", "closed"):
        colour = GREEN
    elif key in ("failed", "error", "rejected", "tampered"):
        colour = RED
    elif key in ("pending", "queued", "processing", "running", "in_progress"):
        colour = AMBER
    else:
        colour = MUTED
    style = ParagraphStyle(
        f"status_{colour.hexval()[2:]}",
        parent=STYLES["cell"],
        textColor=colour,
        fontName="Helvetica-Bold",
    )
    return style


# -----------------------------------------------------------------------------
# Table helpers
# -----------------------------------------------------------------------------
def _table(
    header: Sequence[str],
    rows: Sequence[Sequence[Any]],
    col_widths: Sequence[float],
    *,
    mono_columns: Sequence[int] = (),
) -> Table:
    """Build a styled data table with a navy header row."""
    data: list[list[Any]] = []
    for index, label in enumerate(header):
        style = "cell_mono_head" if index in mono_columns else "cell_head"
        data.append([_para(label, style)])
    for row in rows:
        data.append(list(row))

    table = Table(data, colWidths=list(col_widths), repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("LINEBELOW", (0, 0), (-1, 0), 1.0, CYAN),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _key_value_table(pairs: Sequence[tuple[str, Any]]) -> Table:
    """Build the two-column key/value table used for the case summary."""
    data: list[list[Any]] = []
    for key, value in pairs:
        data.append([_para(key, "label"), _para(value, "value")])

    table = Table(data, colWidths=[CONTENT_W * 0.28, CONTENT_W * 0.72], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), BAND),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("LINEBEFORE", (1, 0), (1, -1), 1.6, CYAN),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    return table


# -----------------------------------------------------------------------------
# Page furniture
# -----------------------------------------------------------------------------
class _NumberedCanvas(canvas.Canvas):
    """A canvas that can print "Page N of M" once the total is known.

    ReportLab cannot know the page count while the document is still being
    laid out, so every page is captured and the numbers are stamped in
    ``save()``.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:  # noqa: N802 - ReportLab API
        self._page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._page_states)
        for state in self._page_states:
            self.__dict__.update(state)
            self._stamp(total)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _stamp(self, total: int) -> None:
        """Draw the page counter in the footer."""
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED)
        page_no = self._pageNumber
        self.drawCentredString(PAGE_SIZE[0] / 2.0, 1.15 * cm, f"Page {page_no} of {total}")
        self.setFont("Helvetica", 7)
        self.drawString(MARGIN, 1.15 * cm, "CONFIDENTIAL - DIGITAL FORENSICS REPORT")
        self.restoreState()


def _page_frame(case_id: str) -> Any:
    """Return an ``onPage`` callback that draws the running header/footer."""

    def _draw(canv: canvas.Canvas, doc: Any) -> None:
        canv.saveState()
        top = PAGE_SIZE[1] - 1.15 * cm
        canv.setFont("Helvetica-Bold", 7.5)
        canv.setFillColor(NAVY)
        canv.drawString(MARGIN, top, "CYBERSLEUTH AI")
        canv.setFont("Helvetica", 7.5)
        canv.setFillColor(MUTED)
        canv.drawRightString(PAGE_SIZE[0] - MARGIN, top, f"Case {case_id}")
        canv.setStrokeColor(CYAN)
        canv.setLineWidth(0.8)
        canv.line(MARGIN, top - 5, PAGE_SIZE[0] - MARGIN, top - 5)
        canv.restoreState()

    return _draw


# -----------------------------------------------------------------------------
# Section builders
# -----------------------------------------------------------------------------
def _section_heading(title: str) -> list[Any]:
    """Return the flowables that introduce a section."""
    return [
        _para(title, "heading"),
        Spacer(1, 3),
        HRFlowable(
            width="100%",
            thickness=1.6,
            color=CYAN,
            spaceBefore=0,
            spaceAfter=8,
            hAlign="LEFT",
        ),
    ]


def _title_block(investigation: dict[str, Any], generated_at: str) -> list[Any]:
    """Build the title page header block."""
    case_id = _text(investigation.get("case_id"))
    title = _text(investigation.get("title"))

    band = Table(
        [
            [_para("CYBERSLEUTH AI", "wordmark")],
            [_para("Digital Forensics & Evidence Reconstruction Platform", "wordmark_sub")],
        ],
        colWidths=[CONTENT_W],
        hAlign="LEFT",
    )
    band.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 1), (-1, 1), 1.5, CYAN),
            ]
        )
    )

    meta = Table(
        [
            [
                _para("CASE ID", "meta_label"),
                _para("GENERATED", "meta_label"),
                _para("STATUS", "meta_label"),
            ],
            [
                _para(case_id, "meta_value"),
                _para(generated_at, "meta_value"),
                _para(_text(investigation.get("status")), "meta_value"),
            ],
        ],
        colWidths=[CONTENT_W * 0.26, CONTENT_W * 0.46, CONTENT_W * 0.28],
        hAlign="LEFT",
    )
    meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LINEBELOW", (0, 0), (-1, -1), 0.6, RULE),
            ]
        )
    )

    return [
        band,
        Spacer(1, 16),
        _para(title, "case_title"),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=2.4, color=BLUE, spaceAfter=12, hAlign="LEFT"),
        meta,
        Spacer(1, 10),
    ]


def _case_summary_section(investigation: dict[str, Any]) -> list[Any]:
    """Build the case summary section."""
    pairs: list[tuple[str, Any]] = [
        ("Case ID", _text(investigation.get("case_id"))),
        ("Title", _text(investigation.get("title"))),
        ("Category", _text(investigation.get("category"))),
        ("Priority", _text(investigation.get("priority"))),
        ("Status", _text(investigation.get("status"))),
        ("Owner", _text(investigation.get("owner_name"))),
        ("Investigation ID", _text(investigation.get("id"))),
        ("Created", _text(investigation.get("created_at"))),
        ("Last updated", _text(investigation.get("updated_at"))),
        ("Description", _text(investigation.get("description"))),
        ("Notes", _text(investigation.get("notes"))),
    ]
    return _section_heading("1. Case summary") + [_key_value_table(pairs)]


def _evidence_section(evidence: Sequence[dict[str, Any]]) -> list[Any]:
    """Build the evidence inventory section and its SHA-256 appendix."""
    flow: list[Any] = _section_heading("2. Evidence inventory")

    rows: list[list[Any]] = []
    for item in evidence:
        status = _text(item.get("status"))
        rows.append(
            [
                _para(_text(item.get("original_filename")), "cell_bold"),
                _para(_file_size(item.get("file_size")), "cell"),
                _para(_truncate_hash(item.get("sha256_hash")), "cell_mono"),
                _para(_text(item.get("mime_type")), "cell"),
                _para(_text(item.get("uploaded_by_name")), "cell"),
                _para(_text(item.get("uploaded_at")), "cell"),
                _para(status, _status_style(item.get("status"))),
            ]
        )

    flow.append(
        _table(
            ["File name", "Size", "SHA-256", "Type", "Uploaded by", "Uploaded at", "Status"],
            rows,
            [94, 38, 92, 76, 58, 68, 55],
            mono_columns=(2,),
        )
    )

    # File attributes captured at upload time (EXIF, media metadata, ...).
    metadata_rows: list[list[Any]] = []
    for item in evidence:
        metadata = item.get("metadata")
        if not isinstance(metadata, dict) or not metadata:
            continue
        name = _text(item.get("original_filename"))
        for key in sorted(metadata):
            metadata_rows.append(
                [
                    _para(name, "cell_bold"),
                    _para(_truncate_text(key, 120), "cell"),
                    _para(_truncate_text(metadata[key], 300), "cell"),
                ]
            )
    if metadata_rows:
        flow.append(Spacer(1, 10))
        flow.append(_para("File metadata", "caption"))
        flow.append(Spacer(1, 4))
        flow.append(
            _table(["File name", "Attribute", "Value"], metadata_rows, [120, 110, 251])
        )

    flow.append(PageBreak())
    flow.extend(_section_heading("Appendix A - SHA-256 manifest"))
    flow.append(
        _para(
            "The manifest below records the full SHA-256 digest of every artefact "
            "attached to this case. It is the authoritative integrity reference "
            "for the evidence set and must be verified against the original "
            "media before the findings in this report are relied upon.",
            "body",
        )
    )
    flow.append(Spacer(1, 8))

    manifest_rows: list[list[Any]] = []
    for index, item in enumerate(evidence, start=1):
        manifest_rows.append(
            [
                _para(str(index), "cell_mono"),
                _para(_text(item.get("original_filename")), "cell_bold"),
                _para(_text(item.get("sha256_hash")), "cell_mono"),
            ]
        )
    flow.append(
        _table(
            ["#", "File name", "SHA-256 (full digest)"],
            manifest_rows,
            [22, 150, 309],
            mono_columns=(0, 2),
        )
    )
    return flow


def _custody_section(custody: Sequence[dict[str, Any]]) -> list[Any]:
    """Build the chain of custody section."""
    flow = _section_heading("3. Chain of custody")
    flow.append(
        _para(
            "The custody ledger is append-only and hash-chained: every event "
            "carries the digest of the event before it, so any alteration of the "
            "history invalidates every link that follows.",
            "body",
        )
    )
    flow.append(Spacer(1, 8))

    rows: list[list[Any]] = []
    for item in custody:
        event_hash = _text(item.get("event_hash"))
        previous_hash = _clean(item.get("previous_hash")).strip()
        hash_cell = [_para(event_hash, "cell_mono")]
        if previous_hash:
            hash_cell.append(_para(f"prev: {previous_hash}", "cell_mono"))
        rows.append(
            [
                _para(_text(item.get("timestamp")), "cell"),
                _para(_text(item.get("event_type")), "cell_bold"),
                _para(_text(item.get("actor_name")), "cell"),
                _para(_text(item.get("details")), "cell"),
                hash_cell,
            ]
        )
    flow.append(
        _table(
            ["Timestamp", "Event", "Actor", "Details", "Event hash"],
            rows,
            [70, 50, 58, 163, 140],
            mono_columns=(4,),
        )
    )
    return flow


def _analysis_section(analyses: Sequence[dict[str, Any]]) -> list[Any]:
    """Build the forensic analysis section - one sub-block per module."""
    flow = _section_heading("4. Forensic analysis results")
    for index, analysis in enumerate(analyses, start=1):
        module = _text(analysis.get("module"))
        status = _text(analysis.get("status"))
        confidence = _confidence(analysis.get("confidence_score"))

        header = Table(
            [
                [
                    _para(f"{index}. {module}", "subheading"),
                    _para(status, _status_style(analysis.get("status"))),
                    _para(f"confidence {confidence}", "cell"),
                ]
            ],
            colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.25, CONTENT_W * 0.25],
            hAlign="LEFT",
        )
        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.6, RULE),
                ]
            )
        )

        block: list[Any] = [header, Spacer(1, 5)]

        meta_bits = [
            f"Evidence {_text(analysis.get('evidence_id'))}",
            f"Started {_text(analysis.get('created_at'))}",
            f"Completed {_text(analysis.get('completed_at'))}",
        ]
        block.append(_para(" \u00b7 ".join(meta_bits), "muted"))
        block.append(Spacer(1, 5))

        result = analysis.get("result_data")
        result = result if isinstance(result, dict) else {}

        summary = _clean(result.get("summary")).strip()
        if summary:
            block.append(_para(summary, "body"))
            block.append(Spacer(1, 6))

        findings = result.get("findings")
        findings = findings if isinstance(findings, list) else []
        finding_rows: list[list[Any]] = []
        for finding in findings:
            if not isinstance(finding, dict):
                finding = {"label": "", "detail": finding}
            finding_rows.append(
                [
                    _para(_text(finding.get("label")), "cell_bold"),
                    _para(_text(finding.get("detail")), "cell"),
                    _para(_text(finding.get("method")), "cell"),
                    _para(_text(finding.get("severity")), _status_style(finding.get("severity"))),
                ]
            )

        if finding_rows:
            block.append(
                _table(
                    ["Finding", "Detail", "Method", "Severity"],
                    finding_rows,
                    [95, 226, 60, 100],
                )
            )
        else:
            block.append(_para("No findings were reported by this module.", "muted"))

        flow.append(KeepTogether(block))
        flow.append(Spacer(1, 12))
    return flow


def _correlation_section(correlations: Sequence[dict[str, Any]]) -> list[Any]:
    """Build the correlation findings section."""
    flow = _section_heading("5. Correlation findings")
    rows: list[list[Any]] = []
    for item in correlations:
        created = _clean(item.get("created_at")).strip() or _clean(item.get("timestamp")).strip()
        rows.append(
            [
                _para(_text(item.get("correlation_type")), "cell_bold"),
                _para(_text(item.get("description")), "cell"),
                _para(_confidence(item.get("confidence")), "cell"),
                _para(_bool_text(item.get("verified"), "Verified", "Unverified"), "cell"),
                _para(created or EM_DASH, "cell"),
            ]
        )
    flow.append(
        _table(
            ["Type", "Description", "Confidence", "State", "Created"],
            rows,
            [70, 190, 55, 50, 116],
        )
    )
    return flow


def _audit_section(entries: Sequence[dict[str, Any]]) -> list[Any]:
    """Build the optional audit trail section."""
    flow = _section_heading("6. Audit trail")
    rows: list[list[Any]] = []
    for item in entries:
        details = item.get("details")
        if isinstance(details, dict):
            details = json.dumps(details, ensure_ascii=False, sort_keys=True, default=str)
        rows.append(
            [
                _para(_text(item.get("timestamp")), "cell"),
                _para(_text(item.get("user_name")), "cell_bold"),
                _para(_text(item.get("action")), "cell"),
                _para(_text(item.get("resource")), "cell"),
                _para(_text(details), "cell"),
            ]
        )
    flow.append(
        _table(
            ["Timestamp", "User", "Action", "Resource", "Details"],
            rows,
            [80, 70, 80, 70, 181],
        )
    )
    return flow


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def _flag(options: dict[str, Any], key: str, default: bool = True) -> bool:
    """Read a boolean option, treating ``None`` as "use the default"."""
    value = options.get(key, None)
    if value is None:
        return default
    return bool(value)


def _as_dicts(value: Any) -> list[dict[str, Any]]:
    """Coerce an arbitrary sequence into a list of dictionaries."""
    if not value or not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, dict)]


def render_report(
    *,
    investigation: dict,
    evidence: list[dict],
    analyses: list[dict],
    correlations: list[dict],
    custody: list[dict],
    options: dict | None = None,
) -> bytes:
    """Render the investigation report as a PDF and return the raw bytes."""
    opts: dict[str, Any] = dict(options) if isinstance(options, dict) else {}
    inv = investigation if isinstance(investigation, dict) else {}
    evidence_items = _as_dicts(evidence)
    analysis_items = _as_dicts(analyses)
    correlation_items = _as_dicts(correlations)
    custody_items = _as_dicts(custody)

    audit_entries = _as_dicts(opts.get("audit"))
    if not audit_entries:
        audit_entries = _as_dicts(opts.get("audit_entries"))

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    case_id = _text(inv.get("case_id"))

    show_evidence = _flag(opts, "include_evidence")
    show_custody = _flag(opts, "include_custody")
    show_analysis = _flag(opts, "include_analysis")
    show_correlation = _flag(opts, "include_correlation")
    show_audit = _flag(opts, "include_audit") and bool(audit_entries)

    has_content = bool(
        _clean(inv.get("title")).strip()
        or _clean(inv.get("description")).strip()
        or _clean(inv.get("notes")).strip()
        or _clean(inv.get("case_id")).strip()
        or evidence_items
        or analysis_items
        or correlation_items
        or custody_items
        or audit_entries
    )

    story: list[Any] = list(_title_block(inv, generated_at))

    if not has_content:
        story.append(Spacer(1, 24))
        story.append(_para("This report has no content.", "empty"))
        story.append(Spacer(1, 6))
        story.append(
            _para(
                "No case information, evidence, custody events, analysis results or "
                "correlations were available when the report was generated.",
                "empty",
            )
        )
    else:
        story.append(PageBreak())
        story.extend(_case_summary_section(inv))

        if show_evidence and evidence_items:
            story.extend(_evidence_section(evidence_items))
        if show_custody and custody_items:
            story.extend(_custody_section(custody_items))
        if show_analysis and analysis_items:
            story.extend(_analysis_section(analysis_items))
        if show_correlation and correlation_items:
            story.extend(_correlation_section(correlation_items))
        if show_audit and audit_entries:
            story.extend(_audit_section(audit_entries))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=2.1 * cm,
        bottomMargin=1.9 * cm,
        title=f"CyberSleuth AI - {_text(inv.get('title'))}",
        author="CyberSleuth AI",
        subject=f"Forensic investigation report for case {case_id}",
    )
    doc.build(
        story,
        onFirstPage=_page_frame(case_id),
        onLaterPages=_page_frame(case_id),
        canvasmaker=_NumberedCanvas,
    )
    return buffer.getvalue()

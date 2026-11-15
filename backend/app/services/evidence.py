# =============================================================================
# CYBERSLEUTH AI - Evidence intake (Phase 3)
# =============================================================================
# Validation, hashing and metadata extraction for uploaded originals.
#
# Rules enforced here:
#   1. An upload is rejected when its extension is not allow-listed.
#   2. An upload is rejected when it exceeds the configured size cap.
#   3. The detected content type is compared with the declared extension; a
#      mismatch is recorded as a warning, not a silent acceptance.
#   4. The SHA-256 of the stored bytes is the integrity anchor. It is computed
#      from the bytes that were actually written to storage, never from the
#      upload stream, so the hash describes what was preserved.
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.security import sha256_file

logger = logging.getLogger(__name__)

# Extensions that carry a genuine risk if they are ever executed.
EXECUTABLE_EXTENSIONS = {
    "exe", "dll", "com", "bat", "cmd", "ps1", "vbs", "js", "jse", "wsf",
    "scr", "msi", "hta", "reg", "scpt", "sh", "jar",
}


@dataclass
class ValidationResult:
    """Outcome of validating an uploaded file."""

    valid: bool
    filename: str
    extension: str
    size: int
    detected_mime: str
    declared_mime: str
    sha256: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "extension": self.extension,
            "size": self.size,
            "detected_mime": self.detected_mime,
            "declared_mime": self.declared_mime,
            "sha256": self.sha256,
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
            "error": self.error,
        }


def detect_mime(path: Path, filename: str) -> str:
    """Detect the content type of a file from its bytes, not its name."""
    try:
        import filetype

        kind = filetype.guess(str(path))
        if kind is not None:
            return kind.mime
    except Exception:  # pragma: no cover - filetype is optional at runtime
        logger.debug("filetype detection unavailable", exc_info=True)

    import mimetypes

    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def extract_metadata(path: Path, mime: str) -> Dict[str, Any]:
    """Extract whatever metadata the file format carries.

    Every extractor is best effort: a file that cannot be parsed still yields
    a usable record, it just carries fewer fields.
    """
    metadata: Dict[str, Any] = {}

    if mime.startswith("image/"):
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            with Image.open(path) as image:
                metadata["dimensions"] = {"width": image.width, "height": image.height}
                metadata["format"] = image.format
                metadata["mode"] = image.mode
                exif = image.getexif()
                if exif:
                    metadata["exif"] = {
                        TAGS.get(tag, str(tag)): (
                            value.decode("utf-8", "replace")
                            if isinstance(value, bytes)
                            else str(value)
                        )
                        for tag, value in exif.items()
                    }
        except Exception:
            logger.debug("Image metadata extraction failed", exc_info=True)

    elif mime.startswith("audio/"):
        try:
            import soundfile as sf

            info = sf.info(str(path))
            metadata["audio"] = {
                "sample_rate": int(info.samplerate),
                "channels": int(info.channels),
                "frames": int(info.frames),
                "duration_seconds": round(float(info.duration), 3),
                "format": info.format,
                "subtype": info.subtype,
            }
        except Exception:
            logger.debug("Audio metadata extraction failed", exc_info=True)

    elif mime in ("application/zip", "application/x-zip-compressed"):
        try:
            import zipfile

            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                metadata["archive"] = {
                    "entry_count": len(entries),
                    "uncompressed_bytes": sum(e.file_size for e in entries),
                    "entries": [
                        {"name": e.filename, "size": e.file_size, "compressed": e.compress_size}
                        for e in entries[:200]
                    ],
                }
        except Exception:
            logger.debug("Archive metadata extraction failed", exc_info=True)

    elif mime == "application/pdf":
        try:
            metadata["pdf"] = _pdf_metadata(path)
        except Exception:
            logger.debug("PDF metadata extraction failed", exc_info=True)

    elif mime.startswith("text/"):
        try:
            raw = path.read_bytes()[:8192]
            metadata["text"] = {
                "encoding": "utf-8" if _is_utf8(raw) else "binary",
                "preview": raw.decode("utf-8", "replace")[:2000] if _is_utf8(raw) else None,
            }
        except Exception:
            logger.debug("Text metadata extraction failed", exc_info=True)

    return metadata


def _is_utf8(raw: bytes) -> bool:
    try:
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _pdf_metadata(path: Path) -> Dict[str, Any]:
    """Read the document information dictionary from a PDF without a PDF library."""
    import re

    raw = path.read_bytes()
    info: Dict[str, Any] = {"version": raw[:8].decode("latin-1", "replace").strip()}

    for key in (b"Title", b"Author", b"Subject", b"Creator", b"Producer", b"CreationDate"):
        pattern = re.compile(rb"/" + key + rb"\s*\(([^)]*)\)")
        match = pattern.search(raw)
        if match:
            info[key.decode()] = match.group(1).decode("latin-1", "replace")

    info["page_count_estimate"] = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    info["encrypted"] = b"/Encrypt" in raw
    return info


def validate_upload(
    *,
    path: Path,
    original_filename: str,
    declared_mime: str = "application/octet-stream",
    size: Optional[int] = None,
) -> ValidationResult:
    """Validate an uploaded file and compute its integrity hash."""
    filename = Path(original_filename).name
    extension = Path(filename).suffix.lower().lstrip(".")
    actual_size = size if size is not None else path.stat().st_size
    detected_mime = detect_mime(path, filename)

    result = ValidationResult(
        valid=True,
        filename=filename,
        extension=extension,
        size=actual_size,
        detected_mime=detected_mime,
        declared_mime=declared_mime or detected_mime,
    )

    allowed = settings.allowed_extension_set
    if extension and extension not in allowed:
        result.valid = False
        result.error = (
            f"File type '.{extension}' is not accepted. "
            f"Allowed types: {', '.join(sorted(allowed))}"
        )
        return result

    if not extension:
        result.valid = False
        result.error = "The file has no extension, so its type cannot be validated."
        return result

    if actual_size > settings.max_upload_bytes:
        result.valid = False
        result.error = (
            f"File is {actual_size / (1024 * 1024):.1f} MB, which exceeds the "
            f"{settings.MAX_UPLOAD_SIZE_MB} MB limit."
        )
        return result

    if actual_size == 0:
        result.valid = False
        result.error = "The file is empty."
        return result

    if extension in EXECUTABLE_EXTENSIONS:
        result.warnings.append(
            "This file type can be executed. It is stored as an immutable "
            "original and is never run by the platform."
        )

    if detected_mime != result.declared_mime:
        result.warnings.append(
            f"The declared content type '{result.declared_mime}' does not match the "
            f"detected type '{detected_mime}'."
        )

    result.sha256 = sha256_file(path)
    result.metadata = extract_metadata(path, detected_mime)
    return result

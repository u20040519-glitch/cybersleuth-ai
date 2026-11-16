# =============================================================================
# CYBERSLEUTH AI - DeepTrace AI : image forensics (Phase 4)
# =============================================================================
# Read-only, static analysis of an image file for evidence of tampering.
#
# The module never executes the evidence and never rewrites the original: it
# only reads bytes from disk, and every artefact it produces is written to the
# directory supplied through `options["output_dir"]`.
#
# Checks performed
#   1. Metadata   - EXIF presence and absence, camera identity, editing
#                   software signature, GPS fix and capture timestamps.
#   2. ELA        - Error Level Analysis: the image is recompressed at a known
#                   JPEG quality and the per-pixel error map is analysed.
#   3. Noise      - high-pass residual analysis of the sensor noise profile
#                   and per-block deviation from that profile.
#   4. Copy-move  - hash based region duplication search (heuristic).
#   5. JPEG grid  - discontinuity across 8x8 block edges versus other edges.
#   6. Geometry   - dimensions, aspect ratio, resize and crop detection.
#
# Every check reports a finding whose `method` field states what it really is:
# "measured" for a value computed from the pixels or the metadata, and
# "heuristic" for the copy-move detector, which only produces candidates that
# still need human confirmation.
#
# Rules enforced here:
#   1. A check that cannot be run for a given file says so explicitly instead
#      of being silently dropped.
#   2. No finding is invented. Every number quoted is computed from the file.
#   3. The original file is never modified.
# =============================================================================

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.forensic.base import (
    completed,
    failed,
    finding,
    output_dir,
    timeline_event,
    unavailable,
)

logger = logging.getLogger(__name__)

MODULE = "deeptrace"

try:
    import cv2

    _HAS_CV2 = True
except Exception:  # pragma: no cover - opencv is an optional runtime dependency
    cv2 = None  # type: ignore[assignment]
    _HAS_CV2 = False

try:
    from PIL import ExifTags, Image

    _HAS_PIL = True
except Exception:  # pragma: no cover - pillow is an optional runtime dependency
    Image = None  # type: ignore[assignment]
    ExifTags = None  # type: ignore[assignment]
    _HAS_PIL = False

AVAILABLE = _HAS_CV2 and _HAS_PIL

# --- Tunables ---------------------------------------------------------------
JPEG_QUALITY = 95          # quality used for the Error Level Analysis pass
ELA_REGION = 32           # side of the square region searched for the hotspot
MAX_ANALYSIS_EDGE = 2000  # longest edge used for the pixel level analysis
WORKING_EDGE = 512        # longest edge used for the copy-move search
BLOCK_SIZE = 16           # side of the copy-move block (must divide by HASH_GRID)
HASH_GRID = 8             # cells per side of the mean hash
MAX_GROUP_SIZE = 64       # largest hash bucket that is expanded into pairs
MAX_GROUP_PAIRS = 2000    # pair budget inside a single hash bucket
MAX_CANDIDATE_PAIRS = 12000  # total pair budget for the whole scan
MATCH_MSE = 0.0002        # maximum normalised MSE for a confirmed duplicate
MIN_BLOCK_TEXTURE = 3.0   # minimum block standard deviation to be interesting
MAX_REPORTED_DUPLICATES = 10

# Aspect ratios produced by common sensors and displays.
KNOWN_ASPECT_RATIOS: Dict[str, float] = {
    "3:2 (35mm still camera)": 3 / 2,
    "4:3 (compact camera)": 4 / 3,
    "16:9 (widescreen)": 16 / 9,
    "1:1 (square)": 1.0,
    "9:16 (portrait widescreen)": 9 / 16,
    "21:9 (ultrawide)": 21 / 9,
}

# EXIF tags that matter for a tampering assessment.
EXIF_TAGS: Dict[int, str] = {
    0x010F: "Make",
    0x0110: "Model",
    0x0112: "Orientation",
    0x0131: "Software",
    0x0132: "DateTime",
    0x013B: "Artist",
    0x8298: "Copyright",
    0x9003: "DateTimeOriginal",
    0x9004: "DateTimeDigitized",
    0x9011: "OffsetTimeOriginal",
    0x9012: "OffsetTimeDigitized",
    0xA002: "PixelXDimension",
    0xA003: "PixelYDimension",
}

# Editing tools whose presence in the Software tag is itself a finding.
EDITOR_SIGNATURES = (
    "adobe photoshop",
    "adobe lightroom",
    "gimp",
    "affinity photo",
    "pixelmator",
    "paint.net",
    "face-aware",
    "luminar",
    "snapseed",
)


# =============================================================================
# Small helpers
# =============================================================================
def _sha256_file(path: Path) -> str:
    """Streaming SHA-256 of a file, returned as lowercase hex."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mime_for_format(image_format: Optional[str]) -> str:
    """Map a Pillow image format onto a MIME type."""
    mapping = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "TIFF": "image/tiff",
        "BMP": "image/bmp",
        "GIF": "image/gif",
        "ICO": "image/x-icon",
        "PPM": "image/x-portable-pixmap",
    }
    return mapping.get((image_format or "").upper(), "application/octet-stream")


def _write_png(path: Path, image: np.ndarray) -> bool:
    """Write a PNG through an in-memory buffer so unicode paths are safe."""
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        return False
    try:
        path.write_bytes(buffer.tobytes())
    except OSError:
        logger.debug("Could not write derived image %s", path, exc_info=True)
        return False
    return True


def _rational_to_float(value: Any) -> Optional[float]:
    """Convert an EXIF rational (or a sequence of them) into a float.

    Pillow hands back plain floats for some rational fields and tuples of
    rationals for others, so both shapes are accepted.
    """
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, (list, tuple)):
            if not value:
                return None
            value = value[0]
            if isinstance(value, (int, float)):
                return float(value)
        numerator, denominator = value
        if float(denominator) == 0:
            return None
        return float(numerator) / float(denominator)
    except Exception:
        return None


def _gps_coordinate(value: Any) -> Optional[float]:
    """Convert an EXIF GPS coordinate into decimal degrees.

    The EXIF format stores a coordinate as three rationals (degrees, minutes,
    seconds). A single rational is accepted as decimal degrees.
    """
    try:
        parts = list(value)
    except TypeError:
        return None
    if not parts:
        return None
    if len(parts) == 1:
        return _rational_to_float(parts[0])
    if len(parts) != 3:
        return None
    numbers: List[float] = []
    for part in parts:
        number = _rational_to_float(part)
        if number is None:
            return None
        numbers.append(number)
    degrees, minutes, seconds = numbers
    return degrees + minutes / 60.0 + seconds / 3600.0


def _iso_from_exif_datetime(raw: Any, offset: Any = "") -> Optional[str]:
    """Convert an EXIF timestamp ("2024:05:06 07:08:09") to ISO-8601."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    text = text.replace("/", ":")
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y:%m:%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y:%m:%d"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        iso = parsed.isoformat()
        suffix = str(offset or "").strip()
        if suffix and suffix[0] in "+-":
            iso += suffix
        return iso
    return None


def _load_bgr(path: Path) -> Tuple[Optional[np.ndarray], str]:
    """Decode an image into a three channel BGR array.

    Returns (image, error). The file is opened read-only and is never touched
    again after this call.
    """
    try:
        raw = np.fromfile(str(path), dtype=np.uint8)
    except OSError as exc:
        return None, f"the file could not be read ({exc})"
    if raw.size == 0:
        return None, "the file is empty"
    buffer = cv2.imdecode(raw, cv2.IMREAD_UNCHANGED)
    if buffer is None:
        return None, "the bytes are not a supported image format"
    if buffer.ndim == 2:
        buffer = cv2.cvtColor(buffer, cv2.COLOR_GRAY2BGR)
    elif buffer.shape[2] == 4:
        buffer = cv2.cvtColor(buffer, cv2.COLOR_BGRA2BGR)
    elif buffer.shape[2] != 3:
        buffer = buffer[:, :, :3]
    return buffer, ""


def _analysis_copy(bgr: np.ndarray) -> Tuple[np.ndarray, float]:
    """Return a copy of the image bounded by MAX_ANALYSIS_EDGE, plus the scale."""
    height, width = bgr.shape[:2]
    longest = max(height, width)
    if longest <= MAX_ANALYSIS_EDGE:
        return bgr, 1.0
    scale = MAX_ANALYSIS_EDGE / float(longest)
    resized = cv2.resize(
        bgr,
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
        interpolation=cv2.INTER_AREA,
    )
    return resized, scale


def _working_gray(bgr: np.ndarray) -> np.ndarray:
    """Grayscale working copy bounded by WORKING_EDGE, used by the copy-move scan."""
    height, width = bgr.shape[:2]
    longest = max(height, width)
    scale = min(1.0, WORKING_EDGE / float(longest))
    if scale < 1.0:
        bgr = cv2.resize(
            bgr,
            (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
            interpolation=cv2.INTER_AREA,
        )
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


# =============================================================================
# 1. Metadata / EXIF
# =============================================================================
def _read_exif(path: Path) -> Dict[str, Any]:
    """Collect the EXIF values that matter, plus the raw IFD contents."""
    record: Dict[str, Any] = {
        "present": False,
        "tag_count": 0,
        "make": None,
        "model": None,
        "software": None,
        "orientation": None,
        "artist": None,
        "copyright": None,
        "pixel_width": None,
        "pixel_height": None,
        "date_time_original": None,
        "date_time": None,
        "date_time_digitized": None,
        "offset_time_original": None,
        "gps": None,
        "raw_tags": {},
    }

    with Image.open(path) as image:
        record["format"] = image.format
        record["mode"] = image.mode
        try:
            exif = image.getexif()
        except Exception:
            logger.debug("EXIF block could not be parsed", exc_info=True)
            return record
        if not exif:
            return record

        record["present"] = True
        record["tag_count"] = len(exif)
        for tag, value in exif.items():
            name = EXIF_TAGS.get(tag, ExifTags.TAGS.get(tag, str(tag)) if ExifTags else str(tag))
            record["raw_tags"][name] = str(value)

        record["make"] = exif.get(0x010F)
        record["model"] = exif.get(0x0110)
        record["software"] = exif.get(0x0131)
        record["orientation"] = exif.get(0x0112)
        record["artist"] = exif.get(0x013B)
        record["copyright"] = exif.get(0x8298)
        record["date_time"] = exif.get(0x0132)

        # The Exif sub-IFD (0x8769) carries the capture timestamps.
        try:
            exif_ifd = exif.get_ifd(0x8769) or {}
        except Exception:
            exif_ifd = {}
        record["date_time_original"] = exif_ifd.get(0x9003)
        record["date_time_digitized"] = exif_ifd.get(0x9004)
        record["offset_time_original"] = exif_ifd.get(0x9011)
        record["pixel_width"] = exif_ifd.get(0xA002)
        record["pixel_height"] = exif_ifd.get(0xA003)

        # The GPS sub-IFD (0x8825) carries the geotag.
        try:
            gps_ifd = exif.get_ifd(0x8825) or {}
        except Exception:
            gps_ifd = {}
        if gps_ifd:
            latitude = _gps_coordinate(gps_ifd.get(0x0002))
            longitude = _gps_coordinate(gps_ifd.get(0x0004))
            latitude_ref = str(gps_ifd.get(0x0001, "N")).upper()
            longitude_ref = str(gps_ifd.get(0x0003, "E")).upper()
            if latitude is not None and latitude_ref.startswith("S"):
                latitude = -latitude
            if longitude is not None and longitude_ref.startswith("W"):
                longitude = -longitude
            gps: Dict[str, Any] = {
                "latitude": latitude,
                "longitude": longitude,
                "altitude": _rational_to_float(gps_ifd.get(0x0006)),
                "date_stamp": gps_ifd.get(0x001D),
                "time_stamp": gps_ifd.get(0x0007),
            }
            record["gps"] = gps

    return record


def _metadata_findings(
    exif: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Build the metadata findings, the EXIF timeline and the metadata block."""
    findings: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}

    software = str(exif.get("software") or "")
    make = str(exif.get("make") or "")
    model = str(exif.get("model") or "")

    if not exif.get("present"):
        findings.append(
            finding(
                "EXIF metadata absent",
                "The file carries no EXIF block. Metadata is normally written by the "
                "capture device, so its absence is consistent with a re-save, a "
                "screenshot or a deliberate metadata strip. This is an observation, "
                "not proof of editing.",
                method="measured",
                severity="warning",
                value={"exif_present": False},
            )
        )
        metrics["exif_present"] = False
        metrics["editing_software"] = None
        return findings, timeline, metrics

    metrics["exif_present"] = True
    metrics["editing_software"] = software or None

    present = [name for name in ("make", "model", "software", "orientation") if exif.get(name)]
    absent = [name for name in ("make", "model", "software", "orientation") if not exif.get(name)]
    camera = " ".join(part for part in (make, model) if part).strip()

    findings.append(
        finding(
            "EXIF metadata",
            (
                f"EXIF block present with {exif.get('tag_count')} tags. "
                f"Camera: {camera or 'not recorded'}. "
                f"Software: {software or 'not recorded'}. "
                f"Absent fields: {', '.join(absent) if absent else 'none'}."
            ),
            method="measured",
            severity="info",
            value={
                "tag_count": exif.get("tag_count"),
                "camera": camera or None,
                "software": software or None,
                "present_fields": present,
                "absent_fields": absent,
            },
        )
    )

    # An editing tool that identifies itself in the Software tag is a strong
    # hint that the file has been through an editor.
    lowered = software.lower()
    matched = next((name for name in EDITOR_SIGNATURES if name in lowered), None)
    if matched:
        findings.append(
            finding(
                "Editing software signature",
                f"The Software tag names '{software}', which is a recognised image "
                f"editing tool. The image has therefore been saved by that editor, "
                f"which does not by itself mean the pixels were altered.",
                method="measured",
                severity="warning",
                value=software,
            )
        )

    # GPS is optional, but a present fix is useful context for the timeline.
    gps = exif.get("gps")
    if gps:
        gps_time = _iso_from_exif_datetime(gps.get("date_stamp"))
        raw_time = gps.get("time_stamp")
        if isinstance(raw_time, (list, tuple)) and len(raw_time) == 3:
            parts = [_rational_to_float(item) for item in raw_time]
            if all(part is not None for part in parts):
                hours, minutes, seconds = (int(part) for part in parts)  # type: ignore[misc]
                clock = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                gps_time = f"{gps_time}T{clock}" if gps_time else clock
        if gps_time:
            timeline.append(
                timeline_event(
                    gps_time,
                    "GPS timestamp",
                    source="exif:gps",
                    details="Position and clock time recorded by the capture device.",
                    confidence=1.0,
                )
            )

        if gps.get("latitude") is not None and gps.get("longitude") is not None:
            findings.append(
                finding(
                    "GPS geotag",
                    f"The EXIF block carries a GPS fix at "
                    f"{gps['latitude']:.6f}, {gps['longitude']:.6f}"
                    + (
                        f" with an altitude of {gps['altitude']:.1f} m"
                        if gps.get("altitude") is not None
                        else ""
                    )
                    + ".",
                    method="measured",
                    severity="info",
                    value={"latitude": gps["latitude"], "longitude": gps["longitude"]},
                )
            )
        else:
            findings.append(
                finding(
                    "GPS geotag absent",
                    "The EXIF block holds GPS tags but no usable coordinate pair, so "
                    "the image cannot be placed from its own metadata alone.",
                    method="measured",
                    severity="info",
                    value=None,
                )
            )
    else:
        findings.append(
            finding(
                "GPS geotag absent",
                "No GPS fix is stored in the EXIF block, so the image cannot be "
                "placed from its own metadata alone.",
                method="measured",
                severity="info",
                value=None,
            )
        )

    # Capture timestamps.
    offset = exif.get("offset_time_original")
    original = _iso_from_exif_datetime(exif.get("date_time_original"), offset)
    digitized = _iso_from_exif_datetime(exif.get("date_time_digitized"))
    modified = _iso_from_exif_datetime(exif.get("date_time"))

    for raw_value, iso_value, label, source in (
        (exif.get("date_time_original"), original, "Capture time (DateTimeOriginal)", "exif:datetimeoriginal"),
        (exif.get("date_time_digitized"), digitized, "Digitisation time", "exif:datetimedigitized"),
        (exif.get("date_time"), modified, "File modification time (EXIF DateTime)", "exif:datetime"),
    ):
        if iso_value:
            timeline.append(
                timeline_event(
                    iso_value,
                    label,
                    source=source,
                    details=f"Recorded in the EXIF block as '{raw_value}'.",
                    confidence=1.0,
                )
            )

    if original and modified and original != modified:
        findings.append(
            finding(
                "Capture and modification timestamps differ",
                f"DateTimeOriginal is {original} while the DateTime tag reads "
                f"{modified}. The file was written after the moment described by "
                f"the capture timestamp, which is expected for any edit or "
                f"re-save.",
                method="measured",
                severity="info",
                value={"original": original, "modified": modified},
            )
        )
    elif original:
        findings.append(
            finding(
                "Capture timestamp",
                f"DateTimeOriginal reads {original}, so the moment of capture is "
                f"known from the file itself.",
                method="measured",
                severity="info",
                value=original,
            )
        )

    metrics["date_time_original"] = original
    metrics["date_time"] = modified
    return findings, timeline, metrics


# =============================================================================
# 2. Error Level Analysis
# =============================================================================
def _ela_analysis(
    bgr: np.ndarray,
    artefacts: Optional[Path],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Recompress at a known quality and analyse the per-pixel error map."""
    findings: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {"quality": JPEG_QUALITY}

    ok, encoded = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    if not ok:
        findings.append(
            finding(
                "Error Level Analysis skipped",
                f"The image could not be recompressed at JPEG quality {JPEG_QUALITY}, "
                f"so no error map could be produced.",
                method="measured",
                severity="info",
                value=None,
            )
        )
        return findings, metrics

    recompressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if recompressed is None or recompressed.shape != bgr.shape:
        findings.append(
            finding(
                "Error Level Analysis skipped",
                "The recompressed image could not be decoded back to a comparable "
                "frame, so the error map could not be produced.",
                method="measured",
                severity="info",
                value=None,
            )
        )
        return findings, metrics

    difference = cv2.absdiff(bgr, recompressed).astype(np.float32)
    error_map = difference.mean(axis=2)  # per-pixel mean absolute error

    mean_error = float(error_map.mean())
    std_error = float(error_map.std())
    max_error = float(error_map.max())
    metrics["mean_error"] = round(mean_error, 4)
    metrics["std_error"] = round(std_error, 4)
    metrics["max_error"] = round(max_error, 4)

    # The hottest square region is the classic place to look for a spliced or
    # re-encoded area: it is where the recompression error differs most from
    # the rest of the frame.
    height, width = error_map.shape[:2]
    side = max(4, min(ELA_REGION, height, width))
    kernel = np.ones((side, side), dtype=np.float32)
    region_mean = cv2.filter2D(error_map, -1, kernel, borderType=cv2.BORDER_REFLECT) / float(side * side)
    peak_index = np.unravel_index(int(np.argmax(region_mean)), region_mean.shape)
    peak_y, peak_x = int(peak_index[0]), int(peak_index[1])
    peak_value = float(region_mean[peak_y, peak_x])
    contrast = peak_value / mean_error if mean_error > 0 else 0.0
    metrics["peak_region"] = {"x": peak_x, "y": peak_y, "size": side, "mean_error": round(peak_value, 4)}
    metrics["peak_contrast"] = round(contrast, 3)

    # Write the heat map so an investigator can look at the artefact itself.
    if artefacts is not None:
        scaled = error_map.astype(np.float32)
        ceiling = float(np.percentile(scaled, 99.5)) or 1.0
        normalized = np.clip(scaled / ceiling, 0.0, 1.0)
        heatmap = cv2.applyColorMap((normalized * 255.0).astype(np.uint8), cv2.COLORMAP_JET)
        _write_png(artefacts / "ela_heatmap.png", heatmap)

    severity = "warning" if contrast >= 3.0 else "info"
    findings.append(
        finding(
            "Error Level Analysis",
            (
                f"Recompressed at JPEG quality {JPEG_QUALITY}. Error map mean "
                f"{mean_error:.3f}, standard deviation {std_error:.3f}, peak "
                f"{max_error:.0f}. The hottest {side}x{side} region sits at "
                f"x={peak_x}, y={peak_y} with a mean error of {peak_value:.3f} "
                f"({contrast:.2f}x the image average). A region that stands far "
                f"above the average usually indicates content that was encoded "
                f"separately from the rest of the frame."
            ),
            method="measured",
            severity=severity,
            value={
                "quality": JPEG_QUALITY,
                "mean_error": round(mean_error, 4),
                "std_error": round(std_error, 4),
                "peak_region": metrics["peak_region"],
                "peak_contrast": round(contrast, 3),
            },
        )
    )
    return findings, metrics


# =============================================================================
# 3. Noise residual analysis
# =============================================================================
def _noise_analysis(
    bgr: np.ndarray,
    artefacts: Optional[Path],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Estimate the sensor noise floor and look for blocks that break the pattern."""
    findings: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    smoothed = cv2.medianBlur(gray, 3)
    residual = gray.astype(np.float32) - smoothed.astype(np.float32)

    global_std = float(residual.std())
    metrics["global_residual_std"] = round(global_std, 4)

    # Flat regions carry the true sensor noise, because there is no texture to
    # be mistaken for noise.
    smooth_f = smoothed.astype(np.float32)
    local_mean = cv2.boxFilter(smooth_f, -1, (9, 9))
    local_sq_mean = cv2.boxFilter(smooth_f * smooth_f, -1, (9, 9))
    local_std = np.sqrt(np.maximum(local_sq_mean - local_mean * local_mean, 0.0))
    flat_mask = local_std <= 1.5
    flat_pixels = int(flat_mask.sum())

    if flat_pixels >= 200:
        flat_std = float(residual[flat_mask].std())
        flat_abs_mean = float(np.abs(residual[flat_mask]).mean())
        metrics["flat_residual_std"] = round(flat_std, 4)
        metrics["flat_pixel_count"] = flat_pixels
        findings.append(
            finding(
                "Noise residual profile",
                (
                    f"High-pass residual standard deviation is {global_std:.3f} over "
                    f"the whole frame and {flat_std:.3f} inside the {flat_pixels} "
                    f"flat pixels (mean absolute residual {flat_abs_mean:.3f}). The "
                    f"flat region value is the sensor noise floor; a lower value in "
                    f"part of the frame suggests that part was synthesised, heavily "
                    f"filtered or re-encoded."
                ),
                method="measured",
                severity="info",
                value={
                    "global_residual_std": round(global_std, 4),
                    "flat_residual_std": round(flat_std, 4),
                    "flat_pixel_count": flat_pixels,
                },
            )
        )
    else:
        metrics["flat_residual_std"] = None
        findings.append(
            finding(
                "Noise residual profile",
                (
                    f"The high-pass residual standard deviation over the whole frame "
                    f"is {global_std:.3f}. Only {flat_pixels} pixels are flat enough "
                    f"to isolate a sensor noise floor (200 are required), so the "
                    f"flat region estimate was skipped."
                ),
                method="measured",
                severity="info",
                value={"global_residual_std": round(global_std, 4)},
            )
        )

    # Per 8x8 block residual spread: a locally re-encoded or cloned patch
    # breaks the uniform noise profile of the rest of the frame.
    height, width = residual.shape[:2]
    blocks_h = height // 8
    blocks_w = width // 8
    outlier_count = 0
    block_total = 0
    if blocks_h >= 2 and blocks_w >= 2:
        cropped = residual[: blocks_h * 8, : blocks_w * 8]
        tiles = cropped.reshape(blocks_h, 8, blocks_w, 8).transpose(0, 2, 1, 3).reshape(-1, 64)
        block_std = tiles.std(axis=1)
        block_total = int(block_std.size)
        median_block = float(np.median(block_std))
        mad = float(np.median(np.abs(block_std - median_block))) or 1e-6
        upper = median_block + 3.0 * mad
        lower = max(0.0, median_block - 3.0 * mad)
        high = block_std > upper
        low = block_std < lower
        outlier_count = int(high.sum() + low.sum())
        metrics["block_noise_outliers"] = outlier_count
        metrics["block_count"] = block_total
        metrics["block_noise_median"] = round(median_block, 4)

        if outlier_count:
            ratio = outlier_count / float(block_total)
            findings.append(
                finding(
                    "Block-wise noise deviation",
                    (
                        f"{outlier_count} of {block_total} 8x8 blocks have a residual "
                        f"standard deviation outside the robust noise band "
                        f"[{lower:.3f}, {upper:.3f}] around the median {median_block:.3f}. "
                        f"Blocks that differ this much usually carry different "
                        f"encoding or synthesis history from their neighbours."
                    ),
                    method="measured",
                    severity="warning",
                    value={
                        "outlier_blocks": outlier_count,
                        "total_blocks": block_total,
                        "noise_band": [round(lower, 4), round(upper, 4)],
                    },
                )
            )
        else:
            findings.append(
                finding(
                    "Block-wise noise deviation",
                    (
                        f"All {block_total} 8x8 blocks sit inside the robust noise band "
                        f"[{lower:.3f}, {upper:.3f}] around the median {median_block:.3f}. "
                        f"No block shows a different encoding history."
                    ),
                    method="measured",
                    severity="info",
                    value={"outlier_blocks": 0, "total_blocks": block_total},
                )
            )
    else:
        findings.append(
            finding(
                "Block-wise noise deviation skipped",
                f"The analysis frame is {width}x{height} px, too small to hold a "
                f"2x2 grid of 8x8 blocks, so the per-block noise profile was skipped.",
                method="measured",
                severity="info",
                value=None,
            )
        )

    if artefacts is not None:
        amplified = np.clip(residual * 8.0 + 128.0, 0, 255).astype(np.uint8)
        _write_png(artefacts / "noise_residual.png", amplified)

    return findings, metrics


# =============================================================================
# 4. Copy-move detection (heuristic)
# =============================================================================
def _block_hashes(gray: np.ndarray) -> Tuple[np.ndarray, int, int]:
    """Compute a 64 bit mean hash for every overlapping block of the image.

    The block grid is walked row band by row band so that the pixel data is
    never materialised for the whole image at once. A stride of one pixel is
    used so that a duplicated region pasted at any offset still produces a pair
    of blocks that align exactly.
    """
    height, width = gray.shape[:2]
    rows = height - BLOCK_SIZE + 1
    cols = width - BLOCK_SIZE + 1
    total = rows * cols

    windows = np.lib.stride_tricks.sliding_window_view(gray, (BLOCK_SIZE, BLOCK_SIZE))
    weights = np.uint64(1) << np.arange(HASH_GRID * HASH_GRID, dtype=np.uint64)[::-1]
    cell = BLOCK_SIZE // HASH_GRID
    hashes = np.empty(total, dtype=np.uint64)

    for row in range(rows):
        band = np.ascontiguousarray(windows[row]).reshape(cols, BLOCK_SIZE, BLOCK_SIZE)
        # Mean hash: every sub-cell of the block compared against the mean of
        # the whole block, which yields HASH_GRID * HASH_GRID comparable bits.
        cells = (
            band.reshape(cols, HASH_GRID, cell, HASH_GRID, cell)
            .mean(axis=(2, 4))
            .reshape(cols, HASH_GRID * HASH_GRID)
        )
        bits = (cells > cells.mean(axis=1, keepdims=True)).astype(np.uint64)
        hashes[row * cols : (row + 1) * cols] = (bits * weights).sum(axis=1)

    return hashes, rows, cols


def _copy_move_scan(gray: np.ndarray) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Find duplicated regions with block hashes, then confirm them on pixels.

    The scan runs in three stages:

      1. Every overlapping block of the working copy is hashed.
      2. Blocks that share a hash are bucketed together and the buckets are
         expanded into candidate pairs. Buckets that are too large are skipped
         because they describe an ambiguous flat area rather than a copy.
      3. Every candidate pair is confirmed by comparing the actual pixels of
         the two blocks, so a reported duplicate is a pixel level match and not
         just a hash collision.
    """
    findings: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}
    height, width = gray.shape[:2]

    if height < BLOCK_SIZE * 2 or width < BLOCK_SIZE * 2:
        findings.append(
            finding(
                "Copy-move scan skipped",
                f"The working copy is {width}x{height} px, too small for a "
                f"{BLOCK_SIZE}px block search.",
                method="measured",
                severity="info",
                value=None,
            )
        )
        return findings, metrics

    hashes, rows, cols = _block_hashes(gray)
    total = hashes.size

    # Bucket the blocks by hash value.
    _, inverse, counts = np.unique(hashes, return_inverse=True, return_counts=True)
    order = np.argsort(inverse, kind="stable")
    boundaries = np.flatnonzero(np.diff(inverse[order])) + 1
    starts = np.concatenate(([0], boundaries))
    ends = np.concatenate((boundaries, [total]))
    sizes = ends - starts

    usable = np.nonzero((sizes >= 2) & (sizes <= MAX_GROUP_SIZE))[0]
    ambiguous = int(np.count_nonzero(sizes > MAX_GROUP_SIZE))

    left_index: List[int] = []
    right_index: List[int] = []
    for group in usable:
        members = order[starts[group] : ends[group]]
        if len(members) * (len(members) - 1) // 2 > MAX_GROUP_PAIRS:
            # Spread the sample over the bucket so that both copies of a
            # duplicated region are represented.
            step = int(np.ceil(len(members) / 32))
            members = members[::step]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                left_index.append(int(members[i]))
                right_index.append(int(members[j]))
                if len(left_index) >= MAX_CANDIDATE_PAIRS:
                    break
            if len(left_index) >= MAX_CANDIDATE_PAIRS:
                break
        if len(left_index) >= MAX_CANDIDATE_PAIRS:
            break

    metrics["blocks_hashed"] = total
    metrics["candidate_pairs"] = len(left_index)
    metrics["ambiguous_buckets"] = ambiguous

    confirmed: List[Dict[str, Any]] = []
    if left_index:
        left = np.asarray(left_index, dtype=np.int64)
        right = np.asarray(right_index, dtype=np.int64)
        left_y, left_x = np.divmod(left, cols)
        right_y, right_x = np.divmod(right, cols)

        def gather(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
            """Cut the blocks out of the working copy in one vectorised pass."""
            rows_idx = ys[:, None] + np.arange(BLOCK_SIZE)[None, :]
            cols_idx = xs[:, None] + np.arange(BLOCK_SIZE)[None, :]
            return gray[rows_idx[:, :, None], cols_idx[:, None, :]].astype(np.float32)

        block_left = gather(left_x, left_y)
        block_right = gather(right_x, right_y)

        # Two blocks that belong to the same region are not a copy.
        overlapping = (np.abs(left_x - right_x) < BLOCK_SIZE) & (np.abs(left_y - right_y) < BLOCK_SIZE)
        difference = block_left - block_right
        mse = (difference * difference).mean(axis=(1, 2)) / (255.0 ** 2)
        texture = block_left.std(axis=(1, 2))

        keep = (~overlapping) & (mse <= MATCH_MSE) & (texture >= MIN_BLOCK_TEXTURE)
        matched = np.nonzero(keep)[0]

        # Collapse the overlapping confirmations into distinct region pairs.
        for position in matched:
            if len(confirmed) >= MAX_REPORTED_DUPLICATES:
                break
            source_x, source_y = int(left_x[position]), int(left_y[position])
            copy_x, copy_y = int(right_x[position]), int(right_y[position])
            duplicate = False
            for item in confirmed:
                if (
                    abs(item["source"]["x"] - source_x) < BLOCK_SIZE
                    and abs(item["source"]["y"] - source_y) < BLOCK_SIZE
                ) or (
                    abs(item["copy"]["x"] - copy_x) < BLOCK_SIZE
                    and abs(item["copy"]["y"] - copy_y) < BLOCK_SIZE
                ):
                    duplicate = True
                    break
            if duplicate:
                continue
            confirmed.append(
                {
                    "source": {"x": source_x, "y": source_y},
                    "copy": {"x": copy_x, "y": copy_y},
                    "normalised_mse": round(float(mse[position]), 6),
                    "block_size": BLOCK_SIZE,
                }
            )

    metrics["confirmed_duplicates"] = len(confirmed)

    if confirmed:
        preview = "; ".join(
            f"source ({item['source']['x']},{item['source']['y']}) matches copy "
            f"({item['copy']['x']},{item['copy']['y']})"
            for item in confirmed[:MAX_REPORTED_DUPLICATES]
        )
        findings.append(
            finding(
                "Duplicated regions (copy-move)",
                (
                    f"{len(confirmed)} region pairs are pixel level identical inside "
                    f"the {width}x{height} px working copy: {preview}. Duplicated "
                    f"regions are common in composites and in marketing imagery, so "
                    f"this is a lead that needs human confirmation."
                ),
                method="heuristic",
                severity="warning",
                value={"duplicates": confirmed[:MAX_REPORTED_DUPLICATES], "count": len(confirmed)},
            )
        )
    else:
        findings.append(
            finding(
                "Duplicated regions (copy-move)",
                (
                    f"{total} blocks were hashed over the {width}x{height} px working "
                    f"copy, {len(left_index)} candidate pairs were checked against the "
                    f"pixels and none of them matched"
                    + (
                        f"; {ambiguous} hash buckets were skipped because they describe "
                        f"an ambiguous flat area."
                        if ambiguous
                        else "."
                    )
                ),
                method="heuristic",
                severity="info",
                value={"duplicates": [], "count": 0},
            )
        )

    return findings, metrics


# =============================================================================
# 5. JPEG block grid analysis
# =============================================================================
def _block_grid_analysis(gray: np.ndarray) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Measure the discontinuity across 8x8 block edges versus other edges."""
    findings: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}

    height, width = gray.shape[:2]
    if height < 32 or width < 32:
        findings.append(
            finding(
                "JPEG block grid skipped",
                f"The analysis frame is {width}x{height} px, too small to measure a "
                f"block grid.",
                method="measured",
                severity="info",
                value=None,
            )
        )
        return findings, metrics

    plane = gray.astype(np.float32)
    horizontal = np.abs(np.diff(plane, axis=1))  # column-wise gradient
    vertical = np.abs(np.diff(plane, axis=0))  # row-wise gradient

    column_index = np.arange(1, width)
    row_index = np.arange(1, height)
    column_is_block = (column_index % 8) == 0
    row_is_block = (row_index % 8) == 0

    block_column_mean = float(horizontal[:, column_is_block].mean())
    other_column_mean = float(horizontal[:, ~column_is_block].mean())
    block_row_mean = float(vertical[row_is_block, :].mean())
    other_row_mean = float(vertical[~row_is_block, :].mean())

    column_ratio = block_column_mean / other_column_mean if other_column_mean > 0 else 1.0
    row_ratio = block_row_mean / other_row_mean if other_row_mean > 0 else 1.0
    ratio = (column_ratio + row_ratio) / 2.0

    metrics["column_ratio"] = round(column_ratio, 4)
    metrics["row_ratio"] = round(row_ratio, 4)
    metrics["block_ratio"] = round(ratio, 4)

    severity = "warning" if ratio > 1.10 else "info"
    findings.append(
        finding(
            "JPEG block grid",
            (
                f"Mean gradient across 8x8 block edges is {ratio:.4}x the gradient "
                f"across other edges (columns {column_ratio:.4}x, rows "
                f"{row_ratio:.4}x). A ratio near 1.0 means no visible compression "
                f"grid; a ratio clearly above 1.1 is the classic signature of a "
                f"JPEG compressed or re-compressed image."
            ),
            method="measured",
            severity=severity,
            value={
                "column_ratio": round(column_ratio, 4),
                "row_ratio": round(row_ratio, 4),
                "block_ratio": round(ratio, 4),
            },
        )
    )
    return findings, metrics


# =============================================================================
# 6. Geometry / dimensions
# =============================================================================
def _geometry_findings(
    bgr: np.ndarray,
    exif: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Report dimensions, aspect ratio and whether the image was resized."""
    findings: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}

    height, width = bgr.shape[:2]
    aspect = width / float(height) if height else 0.0
    metrics["width"] = width
    metrics["height"] = height
    metrics["aspect_ratio"] = round(aspect, 4)

    findings.append(
        finding(
            "Image dimensions",
            f"The image is {width} x {height} px with an aspect ratio of {aspect:.4f}.",
            method="measured",
            severity="info",
            value={"width": width, "height": height, "aspect_ratio": round(aspect, 4)},
        )
    )

    matched = None
    for name, ratio in KNOWN_ASPECT_RATIOS.items():
        if abs(aspect - ratio) <= 0.02:
            matched = name
            break
    metrics["aspect_match"] = matched

    if matched:
        findings.append(
            finding(
                "Aspect ratio",
                f"The aspect ratio {aspect:.4f} matches {matched}, so the frame has "
                f"not obviously been re-framed.",
                method="measured",
                severity="info",
                value=matched,
            )
        )
    else:
        findings.append(
            finding(
                "Aspect ratio",
                f"The aspect ratio {aspect:.4f} does not match any common sensor or "
                f"display format, which is consistent with a crop or a re-frame.",
                method="measured",
                severity="warning",
                value=round(aspect, 4),
            )
        )

    # Resize detection: the EXIF block sometimes records the dimensions of the
    # sensor image, which is a direct comparison against the stored file.
    exif_width = exif.get("pixel_width")
    exif_height = exif.get("pixel_height")
    try:
        exif_width = int(exif_width) if exif_width is not None else None
        exif_height = int(exif_height) if exif_height is not None else None
    except (TypeError, ValueError):
        exif_width = exif_height = None

    metrics["exif_dimensions"] = {"width": exif_width, "height": exif_height}

    if exif_width and exif_height:
        if (exif_width, exif_height) != (width, height):
            findings.append(
                finding(
                    "Resize detected",
                    f"The EXIF block records {exif_width} x {exif_height} px but the "
                    f"stored image is {width} x {height} px, so the file was resized "
                    f"or cropped after capture.",
                    method="measured",
                    severity="warning",
                    value={"exif": [exif_width, exif_height], "stored": [width, height]},
                )
            )
            metrics["resized"] = True
        else:
            findings.append(
                finding(
                    "No resize detected",
                    f"The EXIF dimensions ({exif_width} x {exif_height} px) match the "
                    f"stored image exactly, so the file was not resized after capture.",
                    method="measured",
                    severity="info",
                    value=None,
                )
            )
            metrics["resized"] = False
    else:
        findings.append(
            finding(
                "Resize check inconclusive",
                "The EXIF block does not record the original pixel dimensions, so "
                "whether the image was resized after capture cannot be established "
                "from the file alone.",
                method="measured",
                severity="info",
                value=None,
            )
        )
        metrics["resized"] = None

    return findings, metrics


# =============================================================================
# Confidence
# =============================================================================
def _confidence_score(metrics: Dict[str, Any]) -> float:
    """Combine the individual measurements into one indication score.

    The score is a documented rule based composite, not a calibrated model
    output, so it must be read as "how much manipulation evidence was found"
    and never as a probability of guilt.

        score = 0.25 * ela + 0.20 * noise + 0.15 * grid
              + 0.15 * copy_move + 0.15 * metadata + 0.10 * geometry

    Each term is clamped to [0, 1]:
      ela       (peak region contrast - 1.5) / 4.0
      noise     fraction of 8x8 blocks outside the noise band, divided by 0.05
      grid      (block edge ratio - 1.05) / 0.35
      copy_move 1.0 when at least one duplicated region was confirmed
      metadata 1.0 for a named editing tool, 0.5 for a missing EXIF block
      geometry 1.0 when a resize was measured, 0.5 for a non standard aspect
    """
    ela = 0.0
    if metrics.get("ela_peak_contrast") is not None:
        ela = (float(metrics["ela_peak_contrast"]) - 1.5) / 4.0

    noise = 0.0
    if metrics.get("block_count"):
        fraction = float(metrics.get("block_noise_outliers", 0)) / float(metrics["block_count"])
        noise = fraction / 0.05

    grid = 0.0
    if metrics.get("block_ratio") is not None:
        grid = (float(metrics["block_ratio"]) - 1.05) / 0.35

    copy_move = 1.0 if metrics.get("confirmed_duplicates") else 0.0

    metadata = 0.0
    if metrics.get("editing_software"):
        metadata = 1.0
    elif metrics.get("exif_present") is False:
        metadata = 0.5

    geometry = 0.0
    if metrics.get("resized") is True:
        geometry = 1.0
    elif metrics.get("aspect_match") is None:
        geometry = 0.5

    def clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    score = (
        0.25 * clamp(ela)
        + 0.20 * clamp(noise)
        + 0.15 * clamp(grid)
        + 0.15 * clamp(copy_move)
        + 0.15 * clamp(metadata)
        + 0.10 * clamp(geometry)
    )
    return round(clamp(score), 4)


# =============================================================================
# Public entry point
# =============================================================================
def analyze(file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse an image file for tampering evidence."""
    options = options or {}
    path = Path(file_path)
    filename = path.name

    if not AVAILABLE:
        return unavailable(
            MODULE,
            "OpenCV and Pillow are required for image forensics but are not installed.",
            filename,
        )

    if not path.is_file():
        return failed(MODULE, "The file does not exist.", filename)

    try:
        bgr, load_error = _load_bgr(path)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("deeptrace could not decode %s", path)
        return failed(MODULE, f"The image could not be decoded ({exc}).", filename)

    if bgr is None:
        return failed(MODULE, f"The file is not a usable image: {load_error}.", filename)

    try:
        artefacts = output_dir(options)
    except Exception:  # pragma: no cover - defensive
        logger.exception("deeptrace could not create the output directory")
        artefacts = None

    findings: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
    derived_files: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}

    try:
        # --- metadata ------------------------------------------------------
        try:
            exif = _read_exif(path)
        except Exception as exc:
            logger.debug("EXIF read failed", exc_info=True)
            exif = {
                "present": False,
                "tag_count": 0,
                "make": None,
                "model": None,
                "software": None,
                "orientation": None,
                "artist": None,
                "copyright": None,
                "pixel_width": None,
                "pixel_height": None,
                "date_time_original": None,
                "date_time": None,
                "date_time_digitized": None,
                "offset_time_original": None,
                "gps": None,
                "raw_tags": {},
                "format": None,
                "mode": None,
            }
            findings.append(
                finding(
                    "EXIF metadata unreadable",
                    f"The metadata block could not be parsed ({exc}); every other "
                    f"check was still performed on the pixel data.",
                    method="measured",
                    severity="info",
                    value=None,
                )
            )

        meta_findings, meta_timeline, meta_metrics = _metadata_findings(exif)
        findings.extend(meta_findings)
        timeline.extend(meta_timeline)
        metrics.update(meta_metrics)

        # --- pixel level analysis -----------------------------------------
        analysis_image, scale = _analysis_copy(bgr)
        if scale < 1.0:
            findings.append(
                finding(
                    "Analysis resolution",
                    f"The image was analysed on a {analysis_image.shape[1]} x "
                    f"{analysis_image.shape[0]} px working copy (scale "
                    f"{scale:.3f}) so the pixel statistics stay tractable.",
                    method="measured",
                    severity="info",
                    value={"scale": round(scale, 4)},
                )
            )

        ela_findings, ela_metrics = _ela_analysis(analysis_image, artefacts)
        findings.extend(ela_findings)
        metrics["ela_peak_contrast"] = ela_metrics.get("peak_contrast")
        metrics["ela_mean_error"] = ela_metrics.get("mean_error")
        metadata["ela"] = ela_metrics

        noise_findings, noise_metrics = _noise_analysis(analysis_image, artefacts)
        findings.extend(noise_findings)
        metrics.update(noise_metrics)
        metadata["noise"] = noise_metrics

        gray_analysis = cv2.cvtColor(analysis_image, cv2.COLOR_BGR2GRAY)
        grid_findings, grid_metrics = _block_grid_analysis(gray_analysis)
        findings.extend(grid_findings)
        metrics["block_ratio"] = grid_metrics.get("block_ratio")
        metadata["block_grid"] = grid_metrics

        copy_findings, copy_metrics = _copy_move_scan(_working_gray(bgr))
        findings.extend(copy_findings)
        metrics["confirmed_duplicates"] = copy_metrics.get("confirmed_duplicates", 0)
        metadata["copy_move"] = copy_metrics

        geometry_findings, geometry_metrics = _geometry_findings(bgr, exif)
        findings.extend(geometry_findings)
        metrics.update(geometry_metrics)

        # --- derived artefacts ---------------------------------------------
        if artefacts is not None:
            thumbnail = _thumbnail(bgr)
            if _write_png(artefacts / "thumbnail.png", thumbnail):
                derived_files.append(
                    {
                        "name": "thumbnail.png",
                        "path": str(artefacts / "thumbnail.png"),
                        "kind": "thumbnail",
                    }
                )
            if (artefacts / "ela_heatmap.png").exists():
                derived_files.append(
                    {
                        "name": "ela_heatmap.png",
                        "path": str(artefacts / "ela_heatmap.png"),
                        "kind": "ela",
                    }
                )
            if (artefacts / "noise_residual.png").exists():
                derived_files.append(
                    {
                        "name": "noise_residual.png",
                        "path": str(artefacts / "noise_residual.png"),
                        "kind": "noise",
                    }
                )

    except Exception as exc:
        logger.exception("deeptrace failed on %s", path)
        return failed(MODULE, f"Unexpected analysis error: {exc}", filename)

    # --- assemble the result -----------------------------------------------
    height, width = bgr.shape[:2]
    severity_counts: Dict[str, int] = {"info": 0, "warning": 0, "critical": 0}
    for item in findings:
        severity = str(item.get("severity", "info"))
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    metadata.update(
        {
            "format": exif.get("format"),
            "mode": exif.get("mode"),
            "exif_present": bool(exif.get("present")),
            "exif_tag_count": exif.get("tag_count"),
            "make": exif.get("make"),
            "model": exif.get("model"),
            "software": exif.get("software"),
            "orientation": exif.get("orientation"),
            "gps": exif.get("gps"),
            "exif_tags": exif.get("raw_tags", {}),
            "width": width,
            "height": height,
            "aspect_ratio": round(width / float(height), 4) if height else None,
            "analysis_scale": round(scale, 4),
        }
    )

    confidence = _confidence_score(metrics)
    summary = (
        f"{len(findings)} findings across 6 checks "
        f"({severity_counts.get('warning', 0)} warning, "
        f"{severity_counts.get('critical', 0)} critical); "
        f"manipulation evidence score {confidence:.2f}."
    )

    return completed(
        MODULE,
        filename=filename,
        sha256=_sha256_file(path),
        mime=_mime_for_format(exif.get("format")),
        summary=summary,
        findings=findings,
        timeline=timeline,
        metadata=metadata,
        derived_files=derived_files,
        confidence_score=confidence,
        dimensions=f"{width}x{height}",
    )


def _thumbnail(bgr: np.ndarray, edge: int = 256) -> np.ndarray:
    """Build a small preview copy of the image."""
    height, width = bgr.shape[:2]
    longest = max(height, width)
    if longest <= edge:
        return bgr.copy()
    scale = edge / float(longest)
    return cv2.resize(
        bgr,
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
        interpolation=cv2.INTER_AREA,
    )

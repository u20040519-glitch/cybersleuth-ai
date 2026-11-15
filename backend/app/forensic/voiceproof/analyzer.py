# =============================================================================
# CYBERSLEUTH AI - VoiceProof (audio forensics, Phase 4)
# =============================================================================
# VoiceProof inspects an audio recording for statistical signs of splicing,
# re-recording or level manipulation.
#
# What is measured (method="measured"):
#   * the objective signal statistics - sample rate, duration, channel count,
#     peak and RMS amplitude and the proportion of samples sitting at full
#     scale (clipping);
#   * the spectral profile - centroid, rolloff, flatness, zero-crossing rate
#     and the energy distribution across frequency bands;
#   * the segmentation of the file into non-silent segments and silences.
#
# What is inferred (method="heuristic"):
#   * splice candidates - short, unusually regular gaps between segments;
#   * energy discontinuities that land exactly on a segment boundary;
#   * segments whose MFCC fingerprint is far from the rest of the file.
#
# Honesty note: none of these indicators prove that a recording was edited.
# They are statistical patterns that are *consistent with* an edit and that a
# human examiner still has to corroborate. Every wording below therefore says
# "indicates a possible ..." and never "proves" or "confirms".
# =============================================================================

from __future__ import annotations

import hashlib
import logging
import mimetypes
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.forensic.base import (
    completed,
    failed,
    finding,
    output_dir,
    timeline_event,
    unavailable,
)

logger = logging.getLogger(__name__)

MODULE = "voiceproof"

# --- Optional heavy dependencies --------------------------------------------
try:  # pragma: no cover - exercised implicitly by the import
    import librosa
    import numpy as np

    LIBROSA_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - librosa missing on the host
    librosa = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    LIBROSA_IMPORT_ERROR = f"librosa could not be imported: {exc}"

# matplotlib is used only to render the derived PNG artefacts. It is imported
# through the object-oriented API so that no global pyplot backend is touched.
try:  # pragma: no cover - matplotlib is optional
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    MATPLOTLIB_AVAILABLE = True
    MATPLOTLIB_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - matplotlib missing on the host
    Figure = None  # type: ignore[assignment]
    FigureCanvasAgg = None  # type: ignore[assignment]
    MATPLOTLIB_AVAILABLE = False
    MATPLOTLIB_IMPORT_ERROR = f"matplotlib could not be imported: {exc}"

AVAILABLE = librosa is not None

# --- Analysis defaults ------------------------------------------------------
# A segment boundary that moves the short-time RMS level by more than this is
# treated as an energy discontinuity worth reporting.
SPLICE_ENERGY_JUMP_DB = 10.0
# Cosine distance (MFCC) beyond which a segment is an acoustic outlier.
MFCC_OUTLIER_DISTANCE = 0.35
# A gap shorter than this between two non-silent segments is "short".
REGULAR_GAP_MAX_SECONDS = 1.0
# Regularity: the gaps must also be consistent with each other.
REGULAR_GAP_CV = 0.25
# Spectral flatness above this suggests noise rather than speech.
NOISE_FLATNESS_THRESHOLD = 0.30
# Analysis window used for the short-time RMS and the MFCC.
N_FFT = 2048
HOP_LENGTH = 512
N_MELS = 128

# Relative timestamps use a fixed epoch so that "1.5 s into the file" is
# expressed as an unambiguous ISO-8601 instant.
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
# Anchor for converting audio offsets to wall-clock instants. `analyze` sets this
# to the evidence file's modification time before any segment is emitted, so the
# timeline carries a real, disclosed anchor instead of 1970-01-01.
_FILE_EPOCH = EPOCH


# -----------------------------------------------------------------------------
# Small helpers
# -----------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    """Streaming SHA-256 of a file, returned as lowercase hex."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _guess_mime(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _iso_at(offset_seconds: float) -> str:
    """Convert an offset from the start of the file into an ISO-8601 instant."""
    return (_FILE_EPOCH + timedelta(seconds=float(offset_seconds))).isoformat()


def _cosine_distance(left: Any, right: Any) -> float:
    """Cosine distance between two vectors; 0.0 means identical direction."""
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    distance = float(1.0 - (float(np.dot(left, right)) / (left_norm * right_norm)))
    # Avoid reporting a negative zero for two identical fingerprints.
    return 0.0 if abs(distance) < 1e-12 else distance


def _round(value: float, digits: int = 4) -> float:
    return float(round(float(value), digits))


# -----------------------------------------------------------------------------
# Signal analysis
# -----------------------------------------------------------------------------
def _load_audio(path: Path) -> Tuple[Any, int, int]:
    """Decode an audio file.

    Returns the down-mixed mono signal, the native sample rate and the number
    of channels. The sample rate is never resampled: for forensics the native
    rate is part of the evidence.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw, sample_rate = librosa.load(str(path), sr=None, mono=False)
    if raw.ndim == 1:
        return raw, int(sample_rate), 1
    channels = int(raw.shape[0])
    return np.mean(raw, axis=0), int(sample_rate), channels

def _signal_overview(mono: Any, sample_rate: int, channels: int) -> Dict[str, Any]:
    """Objective amplitude statistics of the decoded signal."""
    if mono.size == 0:
        return {
            "sample_rate": sample_rate,
            "channels": channels,
            "duration_seconds": 0.0,
            "frame_count": 0,
            "peak_amplitude": 0.0,
            "rms_amplitude": 0.0,
            "dc_offset": 0.0,
            "clipping_ratio": 0.0,
            "near_clipping_ratio": 0.0,
            "dynamic_range_db": 0.0,
        }

    absolute = np.abs(mono)
    peak = float(np.max(absolute))
    rms = float(np.sqrt(np.mean(np.square(mono))))
    # librosa decodes to floats normalised to [-1, 1]; a sample at (or within a
    # hair of) full scale is a sample that was clipped by the recording chain.
    clipping = float(np.mean(absolute >= 0.999))
    near_clipping = float(np.mean(absolute >= 0.99))

    floor = max(rms, 1e-12)
    dynamic_range = 20.0 * float(np.log10(max(peak, floor) / floor))

    return {
        "sample_rate": sample_rate,
        "channels": channels,
        "duration_seconds": _round(mono.shape[0] / float(sample_rate), 3),
        "frame_count": int(mono.shape[0]),
        "peak_amplitude": _round(peak, 6),
        "rms_amplitude": _round(rms, 6),
        "dc_offset": _round(float(np.mean(mono)), 8),
        "clipping_ratio": _round(clipping, 6),
        "near_clipping_ratio": _round(near_clipping, 6),
        "dynamic_range_db": _round(dynamic_range, 2),
    }


def _spectral_profile(mono: Any, sample_rate: int) -> Tuple[Dict[str, Any], Any, Any]:
    """Spectral descriptors of the signal plus the raw magnitude spectrogram."""
    magnitude = np.abs(
        librosa.stft(mono, n_fft=N_FFT, hop_length=HOP_LENGTH)
    )
    power = magnitude ** 2

    centroid = librosa.feature.spectral_centroid(S=magnitude, sr=sample_rate)[0]
    rolloff = librosa.feature.spectral_rolloff(
        S=magnitude, sr=sample_rate, roll_percent=0.85
    )[0]
    flatness = librosa.feature.spectral_flatness(S=magnitude)[0]
    zero_crossing = librosa.feature.zero_crossing_rate(
        mono, frame_length=N_FFT, hop_length=HOP_LENGTH
    )[0]

    profile = {
        "spectral_centroid_mean_hz": _round(float(np.mean(centroid)), 2),
        "spectral_centroid_std_hz": _round(float(np.std(centroid)), 2),
        "spectral_rolloff_mean_hz": _round(float(np.mean(rolloff)), 2),
        "spectral_flatness_mean": _round(float(np.mean(flatness)), 6),
        "spectral_flatness_max": _round(float(np.max(flatness)), 6),
        "zero_crossing_rate_mean": _round(float(np.mean(zero_crossing)), 6),
        "frame_count": int(magnitude.shape[1]),
    }
    return profile, magnitude, power


def _band_energy(power: Any, sample_rate: int) -> Dict[str, float]:
    """Fraction of the total spectral energy inside each frequency band."""
    frequencies = librosa.fft_frequencies(sr=sample_rate, n_fft=N_FFT)
    nyquist = sample_rate / 2.0

    edges = [
        ("20-300 Hz", 20.0, 300.0),
        ("300-1000 Hz", 300.0, 1000.0),
        ("1000-4000 Hz", 1000.0, 4000.0),
        ("4000-8000 Hz", 4000.0, 8000.0),
        ("8000 Hz - Nyquist", 8000.0, nyquist),
    ]

    total = float(np.sum(power))
    distribution: Dict[str, float] = {}
    for name, low, high in edges:
        if high <= low or low >= nyquist:
            distribution[name] = 0.0
            continue
        mask = (frequencies >= low) & (frequencies < high)
        if not np.any(mask):
            distribution[name] = 0.0
            continue
        band_energy = float(np.sum(power[mask, :]))
        distribution[name] = _round(band_energy / total, 6) if total > 0 else 0.0
    return distribution


def _segmentation(
    mono: Any, sample_rate: int, top_db: float
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split the file into non-silent segments and silent regions."""
    frames = librosa.effects.split(
        mono, top_db=top_db, frame_length=N_FFT, hop_length=HOP_LENGTH
    )
    duration = float(mono.shape[0]) / float(sample_rate)
    if len(frames) == 0 or float(np.max(np.abs(mono))) <= 0.0:
        # The whole file is below the silence threshold (or digitally silent).
        if duration > 0.0:
            return [], [
                {
                    "index": 0,
                    "start": 0.0,
                    "end": _round(duration, 3),
                    "duration": _round(duration, 3),
                }
            ]
        return [], []

    # `librosa.effects.split` returns sample indices, not seconds.
    times = np.asarray(frames, dtype=float) / float(sample_rate)

    segments: List[Dict[str, Any]] = []
    for index, (start, end) in enumerate(times):
        segments.append(
            {
                "index": index,
                "start": _round(float(start), 3),
                "end": _round(float(end), 3),
                "duration": _round(float(end) - float(start), 3),
            }
        )

    silences: List[Dict[str, Any]] = []

    if segments and segments[0]["start"] > 0.0:
        silences.append(
            {
                "index": len(silences),
                "start": 0.0,
                "end": segments[0]["start"],
                "duration": _round(segments[0]["start"], 3),
            }
        )

    for previous, following in zip(segments, segments[1:]):
        if following["start"] > previous["end"]:
            silences.append(
                {
                    "index": len(silences),
                    "start": previous["end"],
                    "end": following["start"],
                    "duration": _round(following["start"] - previous["end"], 3),
                }
            )

    if segments and segments[-1]["end"] < duration:
        silences.append(
            {
                "index": len(silences),
                "start": segments[-1]["end"],
                "end": _round(duration, 3),
                "duration": _round(duration - segments[-1]["end"], 3),
            }
        )

    return segments, silences


def _gaps(segments: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The silent gaps that sit *between* two non-silent segments."""
    gaps: List[Dict[str, Any]] = []
    for previous, following in zip(segments, segments[1:]):
        gaps.append(
            {
                "start": previous["end"],
                "end": following["start"],
                "duration": _round(following["start"] - previous["end"], 3),
            }
        )
    return gaps


def _gaps_are_short_and_regular(gaps: Sequence[Dict[str, Any]]) -> Tuple[bool, float]:
    """Heuristic: are the inter-segment gaps short and uniform?

    Returns (is_suspicious, coefficient_of_variation).
    """
    if len(gaps) < 2:
        return False, 0.0

    durations = np.array([gap["duration"] for gap in gaps], dtype=float)
    mean = float(np.mean(durations))
    if mean <= 0.0:
        return False, 0.0

    variation = float(np.std(durations) / mean)
    short = bool(np.all(durations <= REGULAR_GAP_MAX_SECONDS))
    regular = variation <= REGULAR_GAP_CV
    return (short and regular), _round(variation, 4)


def _energy_discontinuities(
    mono: Any, sample_rate: int, boundaries: Sequence[float]
) -> List[Dict[str, Any]]:
    """Short-time RMS jumps that land exactly on a segment boundary."""
    if mono.size == 0 or not boundaries:
        return []

    rms = librosa.feature.rms(
        y=mono, frame_length=N_FFT, hop_length=HOP_LENGTH
    )[0]
    if rms.size < 4:
        return []

    with np.errstate(divide="ignore"):
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)

    frame_seconds = HOP_LENGTH / float(sample_rate)
    window = max(1, int(round(0.05 / frame_seconds)))  # ~50 ms either side

    discontinuities: List[Dict[str, Any]] = []
    for boundary in boundaries:
        index = int(round(boundary / frame_seconds))
        index = max(1, min(index, rms_db.size - 1))

        before = rms_db[max(0, index - window) : index]
        after = rms_db[index : index + window]
        if before.size == 0 or after.size == 0:
            continue

        before_level = float(np.median(before))
        after_level = float(np.median(after))
        jump = after_level - before_level

        if abs(jump) >= SPLICE_ENERGY_JUMP_DB:
            discontinuities.append(
                {
                    "offset_seconds": _round(boundary, 3),
                    "rms_before_db": _round(before_level, 2),
                    "rms_after_db": _round(after_level, 2),
                    "jump_db": _round(jump, 2),
                    "direction": "rise" if jump > 0 else "drop",
                }
            )
    return discontinuities


def _mfcc_distances(
    mono: Any, sample_rate: int, segments: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Cosine distance of every segment's MFCC fingerprint from the first one."""
    if mono.size == 0 or not segments:
        return []

    mfcc = librosa.feature.mfcc(
        y=mono, sr=sample_rate, n_mfcc=20, n_fft=N_FFT, hop_length=HOP_LENGTH
    )
    frame_times = librosa.frames_to_time(
        np.arange(mfcc.shape[1]), sr=sample_rate, hop_length=HOP_LENGTH
    )

    # Coefficient 0 is the frame energy; it dominates the direction of the
    # vector and would drown out the timbral differences we are after.
    fingerprints: List[Optional[Any]] = []
    for segment in segments:
        mask = (frame_times >= segment["start"]) & (frame_times <= segment["end"])
        if not np.any(mask):
            fingerprints.append(None)
            continue
        fingerprints.append(np.mean(mfcc[1:, mask], axis=1))

    reference = fingerprints[0] if fingerprints else None
    results: List[Dict[str, Any]] = []
    for segment, fingerprint in zip(segments, fingerprints):
        if fingerprint is None:
            results.append(
                {
                    "index": segment["index"],
                    "start": segment["start"],
                    "end": segment["end"],
                    "duration": segment["duration"],
                    "cosine_distance": None,
                    "outlier": False,
                }
            )
            continue

        distance = 0.0 if reference is None else _cosine_distance(fingerprint, reference)
        results.append(
            {
                "index": segment["index"],
                "start": segment["start"],
                "end": segment["end"],
                "duration": segment["duration"],
                "cosine_distance": _round(distance, 4),
                "outlier": bool(distance >= MFCC_OUTLIER_DISTANCE),
            }
        )
    return results


# -----------------------------------------------------------------------------
# Derived artefacts
# -----------------------------------------------------------------------------
def _render_waveform(
    mono: Any, sample_rate: int, segments: Sequence[Dict[str, Any]], target: Path
) -> bool:
    """Write a waveform PNG with the detected segments marked."""
    if not MATPLOTLIB_AVAILABLE or mono.size == 0:
        return False

    try:
        figure = Figure(figsize=(11, 3.4), dpi=120)
        FigureCanvasAgg(figure)
        axes = figure.add_subplot(111)

        duration = float(mono.shape[0]) / float(sample_rate)
        step = max(1, int(mono.shape[0] / 20000))
        times = np.arange(0, mono.shape[0], step) / float(sample_rate)
        axes.plot(times, mono[::step], linewidth=0.4, color="#1f4e79")
        axes.set_xlabel("Time (s)")
        axes.set_ylabel("Amplitude")
        axes.set_title(
            f"Waveform - {duration:.2f} s @ {sample_rate} Hz - "
            f"{len(segments)} non-silent segment(s)"
        )
        axes.set_xlim(0, duration)

        for segment in segments:
            axes.axvspan(
                segment["start"],
                segment["end"],
                color="#2e7d32",
                alpha=0.08,
                linewidth=0,
            )

        figure.tight_layout()
        figure.savefig(target, format="png")
        figure.clear()
        return True
    except Exception:
        logger.debug("Waveform rendering failed", exc_info=True)
        return False


def _render_spectrogram(
    mono: Any, sample_rate: int, target: Path
) -> bool:
    """Write a mel spectrogram PNG."""
    if not MATPLOTLIB_AVAILABLE or mono.size == 0:
        return False

    try:
        magnitude = np.abs(librosa.stft(mono, n_fft=N_FFT, hop_length=HOP_LENGTH))
        power = magnitude ** 2
        mel_spec = librosa.feature.melspectrogram(
            S=power, sr=sample_rate, n_fft=N_FFT, hop_length=HOP_LENGTH, n_mels=N_MELS
        )
        mel_db = librosa.power_to_db(mel_spec, ref=np.max)

        frame_times = librosa.frames_to_time(
            np.arange(mel_db.shape[1]), sr=sample_rate, hop_length=HOP_LENGTH
        )
        mel_edges = librosa.mel_frequencies(
            n_mels=N_MELS + 1, fmin=0.0, fmax=sample_rate / 2.0
        )
        # Band centres keep the 1-D pcolormesh contract (one row per band).
        mel_centres = 0.5 * (mel_edges[:-1] + mel_edges[1:])

        figure = Figure(figsize=(11, 4.0), dpi=120)
        FigureCanvasAgg(figure)
        axes = figure.add_subplot(111)
        mesh = axes.pcolormesh(
            frame_times,
            mel_centres,
            mel_db,
            shading="nearest",
            cmap="magma",
            vmin=float(np.min(mel_db)),
            vmax=float(np.max(mel_db)),
        )
        axes.set_xlabel("Time (s)")
        axes.set_ylabel("Frequency (Hz)")
        axes.set_title("Mel spectrogram (128 bands)")
        figure.colorbar(mesh, ax=axes, label="dB (relative to maximum)")
        figure.tight_layout()
        figure.savefig(target, format="png")
        figure.clear()
        return True
    except Exception:
        logger.debug("Spectrogram rendering failed", exc_info=True)
        return False


def _write_derived_files(
    path: Path,
    mono: Any,
    sample_rate: int,
    segments: Sequence[Dict[str, Any]],
    options: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Render the waveform and spectrogram PNGs into the output directory."""
    directory = output_dir(options)
    if directory is None:
        return []

    stem = path.stem or "audio"
    derived: List[Dict[str, Any]] = []

    waveform_path = directory / f"{stem}_waveform.png"
    if _render_waveform(mono, sample_rate, segments, waveform_path):
        derived.append(
            {
                "name": waveform_path.name,
                "path": str(waveform_path),
                "kind": "waveform",
            }
        )

    spectrogram_path = directory / f"{stem}_spectrogram.png"
    if _render_spectrogram(mono, sample_rate, spectrogram_path):
        derived.append(
            {
                "name": spectrogram_path.name,
                "path": str(spectrogram_path),
                "kind": "spectrogram",
            }
        )

    return derived


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
def analyze(file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse an audio file for indicators of splicing, editing or synthesis."""
    options = options or {}
    path = Path(file_path)
    filename = path.name

    if not AVAILABLE:
        reason = (
            LIBROSA_IMPORT_ERROR
            or "the librosa audio-forensics library is not installed"
        )
        return unavailable(MODULE, reason, filename)

    if not path.exists():
        return failed(MODULE, "the file does not exist", filename)
    if not path.is_file():
        return failed(MODULE, "the path is not a regular file", filename)
    try:
        if path.stat().st_size == 0:
            return failed(MODULE, "the file is empty", filename)
    except OSError as exc:
        return failed(MODULE, f"the file could not be inspected: {exc}", filename)

    global _FILE_EPOCH
    try:
        _FILE_EPOCH = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        _FILE_EPOCH = EPOCH

    try:
        mono, sample_rate, channels = _load_audio(path)
    except Exception as exc:
        logger.debug("Audio decoding failed for %s", path, exc_info=True)
        detail = str(exc).strip()
        reason = f"the file could not be decoded as audio ({type(exc).__name__})"
        if detail:
            reason = f"{reason}: {detail}"
        return failed(MODULE, reason, filename)

    if mono is None or mono.size == 0 or sample_rate <= 0:
        return failed(MODULE, "the file contains no decodable audio samples", filename)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return _analyze_audio(path, mono, sample_rate, channels, options)
    except Exception as exc:  # pragma: no cover - defensive, never leak a trace
        logger.exception("voiceproof analysis failed for %s", path)
        return failed(MODULE, f"the audio could not be analysed: {exc}", filename)


def _analyze_audio(
    path: Path,
    mono: Any,
    sample_rate: int,
    channels: int,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """Run every check on a decoded signal and assemble the module payload."""
    top_db = float(options.get("top_db", 30) or 30)

    overview = _signal_overview(mono, sample_rate, channels)
    profile, _magnitude, power = _spectral_profile(mono, sample_rate)
    bands = _band_energy(power, sample_rate)
    segments, silences = _segmentation(mono, sample_rate, top_db)
    gaps = _gaps(segments)
    regular_gaps, gap_variation = _gaps_are_short_and_regular(gaps)

    boundaries = [segment["start"] for segment in segments[1:]]
    discontinuities = _energy_discontinuities(mono, sample_rate, boundaries)
    distances = _mfcc_distances(mono, sample_rate, segments)

    findings: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []

    # --- Signal overview (measured) ----------------------------------------
    findings.append(
        finding(
            "Signal overview",
            (
                f"{overview['duration_seconds']:.2f} s at {sample_rate} Hz, "
                f"{channels} channel(s); peak amplitude {overview['peak_amplitude']:.4f}, "
                f"RMS {overview['rms_amplitude']:.4f}, "
                f"dynamic range {overview['dynamic_range_db']:.1f} dB."
            ),
            method="measured",
            severity="info",
            value=overview,
        )
    )

    if overview["clipping_ratio"] > 0.0:
        findings.append(
            finding(
                "Clipping detected",
                (
                    f"{overview['clipping_ratio'] * 100:.3f}% of the samples sit at full "
                    f"scale (>= 0.999) and {overview['near_clipping_ratio'] * 100:.3f}% "
                    "sit within 1% of it."
                ),
                method="measured",
                severity="low" if overview["clipping_ratio"] < 0.001 else "medium",
                value={
                    "clipping_ratio": overview["clipping_ratio"],
                    "near_clipping_ratio": overview["near_clipping_ratio"],
                },
            )
        )
        findings.append(
            finding(
                "Possible level manipulation",
                (
                    "Saturated samples are consistent with a recording chain that was "
                    "driven too hard or with a gain stage that was applied after the "
                    "original capture; this alone does not establish that the file was "
                    "edited."
                ),
                method="heuristic",
                severity="low",
                value=overview["clipping_ratio"],
            )
        )

    # --- Spectral profile (measured) ---------------------------------------
    findings.append(
        finding(
            "Spectral profile",
            (
                f"Centroid {profile['spectral_centroid_mean_hz']:.0f} Hz "
                f"(sd {profile['spectral_centroid_std_hz']:.0f} Hz), "
                f"rolloff {profile['spectral_rolloff_mean_hz']:.0f} Hz, "
                f"flatness {profile['spectral_flatness_mean']:.4f}, "
                f"zero-crossing rate {profile['zero_crossing_rate_mean']:.4f}."
            ),
            method="measured",
            severity="info",
            value=profile,
        )
    )

    findings.append(
        finding(
            "Spectral band distribution",
            "; ".join(f"{name}: {share * 100:.1f}%" for name, share in bands.items()),
            method="measured",
            severity="info",
            value=bands,
        )
    )

    if profile["spectral_flatness_mean"] >= NOISE_FLATNESS_THRESHOLD:
        findings.append(
            finding(
                "Noise-like spectrum",
                (
                    f"The mean spectral flatness is "
                    f"{profile['spectral_flatness_mean']:.4f}, which is high enough that "
                    "the energy is spread evenly across frequency. That is characteristic "
                    "of noise or hiss rather than of speech, and is worth noting before "
                    "interpreting any other statistic in this file."
                ),
                method="heuristic",
                severity="low",
                value=profile["spectral_flatness_mean"],
            )
        )

    # --- Segmentation (measured) --------------------------------------------
    total_silence = _round(sum(silence["duration"] for silence in silences), 3)
    findings.append(
        finding(
            "Silence and segmentation",
            (
                f"The file splits into {len(segments)} non-silent segment(s) with "
                f"{total_silence:.2f} s of silence in total "
                f"(threshold {top_db:.0f} dB below the peak frame)."
            ),
            method="measured",
            severity="info",
            value={"segments": segments, "silences": silences},
        )
    )

    for segment in segments:
        timeline.append(
            timeline_event(
                _iso_at(segment["start"]),
                f"Segment {segment['index'] + 1} start",
                source=MODULE,
                details=(
                    f"Non-silent segment from {segment['start']:.3f} s to "
                    f"{segment['end']:.3f} s (duration {segment['duration']:.3f} s)."
                ),
                confidence=1.0,
            )
        )

    for silence in silences:
        timeline.append(
            timeline_event(
                _iso_at(silence["start"]),
                f"Silence at {silence['start']:.3f} s",
                source=MODULE,
                details=(
                    f"Silent region from {silence['start']:.3f} s to "
                    f"{silence['end']:.3f} s (duration {silence['duration']:.3f} s)."
                ),
                confidence=1.0,
            )
        )

    # --- Splice heuristics --------------------------------------------------
    if regular_gaps:
        findings.append(
            finding(
                "Regular short gaps between segments",
                (
                    f"{len(gaps)} gap(s) separate the segments and all of them are "
                    f"shorter than {REGULAR_GAP_MAX_SECONDS:.1f} s with a low variation "
                    f"(coefficient of variation {gap_variation:.3f}). A cut-and-paste "
                    "edit often leaves a regular seam, so this pattern is consistent "
                    "with - but does not demonstrate - splicing."
                ),
                method="heuristic",
                severity="medium",
                value={"gaps": gaps, "coefficient_of_variation": gap_variation},
            )
        )

    for discontinuity in discontinuities:
        offset = discontinuity["offset_seconds"]
        findings.append(
            finding(
                f"Possible splice at {offset:.3f} s",
                (
                    f"The short-time RMS level changes by "
                    f"{abs(discontinuity['jump_db']):.1f} dB "
                    f"({discontinuity['direction']}) exactly at the boundary of two "
                    f"segments, from {discontinuity['rms_before_db']:.1f} dB to "
                    f"{discontinuity['rms_after_db']:.1f} dB. This indicates a possible "
                    "splice at that point; a natural change in the recording could "
                    "produce the same signature."
                ),
                method="heuristic",
                severity="medium",
                value=discontinuity,
            )
        )
        timeline.append(
            timeline_event(
                _iso_at(offset),
                f"Possible splice at {offset:.3f} s",
                source=MODULE,
                details=(
                    f"Short-time RMS changes by {discontinuity['jump_db']:.1f} dB at a "
                    "segment boundary."
                ),
                confidence=0.5,
            )
        )

    for distance in distances:
        if not distance["outlier"]:
            continue
        offset = distance["start"]
        findings.append(
            finding(
                f"Outlier segment at {offset:.3f} s",
                (
                    f"The mean MFCC vector of this segment is at a cosine distance of "
                    f"{distance['cosine_distance']:.3f} from the first segment, so it is "
                    "acoustically unlike the rest of the file. A segment that was "
                    "recorded elsewhere and pasted in would look like this; so would a "
                    "speaker or a recording condition that simply changed."
                ),
                method="heuristic",
                severity="medium",
                value=distance,
            )
        )
        timeline.append(
            timeline_event(
                _iso_at(offset),
                f"Outlier segment at {offset:.3f} s",
                source=MODULE,
                details=(
                    f"MFCC cosine distance {distance['cosine_distance']:.3f} from the "
                    "first segment."
                ),
                confidence=0.5,
            )
        )

    # --- Derived artefacts --------------------------------------------------
    derived_files = _write_derived_files(path, mono, sample_rate, segments, options)

    candidate_count = len(discontinuities) + sum(
        1 for distance in distances if distance["outlier"]
    )
    summary = (
        f"{overview['duration_seconds']:.2f} s @ {sample_rate} Hz, {channels} channel(s); "
        f"{len(segments)} segment(s), {len(silences)} silence(s), "
        f"{candidate_count} possible splice indicator(s)."
    )

    metadata = {
        "signal": overview,
        "spectral": profile,
        "band_energy": bands,
        "segments": segments,
        "silent_regions": silences,
        "inter_segment_gaps": gaps,
        "gaps_short_and_regular": regular_gaps,
        "gap_coefficient_of_variation": gap_variation,
        "energy_discontinuities": discontinuities,
        "mfcc_distances": distances,
        "thresholds": {
            "silence_top_db": top_db,
            "splice_energy_jump_db": SPLICE_ENERGY_JUMP_DB,
            "mfcc_outlier_distance": MFCC_OUTLIER_DISTANCE,
            "regular_gap_max_seconds": REGULAR_GAP_MAX_SECONDS,
            "regular_gap_coefficient_of_variation": REGULAR_GAP_CV,
            "noise_flatness_threshold": NOISE_FLATNESS_THRESHOLD,
        },
        "limitations": (
            "These are statistical indicators only. A splice indicator means the "
            "signal is consistent with an edit, not that the file was edited; "
            "compression, gain changes and a change of speaker produce the same "
            "patterns."
        ),
    }

    return completed(
        MODULE,
        filename=path.name,
        sha256=_sha256(path),
        mime=_guess_mime(path),
        summary=summary,
        findings=findings,
        timeline=timeline,
        metadata=metadata,
        derived_files=derived_files,
        confidence_score=None,
        dimensions=f"{channels} ch @ {sample_rate} Hz",
    )

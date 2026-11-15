# =============================================================================
# CYBERSLEUTH AI - Storage service
# =============================================================================
# Three buckets with different guarantees:
#
#   evidence-originals  immutable - the uploaded bytes, never rewritten
#   evidence-derived    derived artefacts produced by the forensic pipeline
#   reports             rendered PDF reports
#
# The same interface is served by the local filesystem backend and by Supabase
# Storage, so the rest of the application never needs to know which is active.
# =============================================================================

from __future__ import annotations

import logging
import mimetypes
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO, Optional
from uuid import UUID

from app.core.config import settings
from app.core.security import constant_time_equals, sha256_text

logger = logging.getLogger(__name__)

BUCKET_ORIGINALS = "evidence-originals"
BUCKET_DERIVED = "evidence-derived"
BUCKET_REPORTS = "reports"

IMMUTABLE_BUCKETS = {BUCKET_ORIGINALS}


class StorageError(RuntimeError):
    """Raised when an object cannot be read or written."""


def build_key(bucket: str, investigation_id: UUID, filename: str, subdir: str = "") -> str:
    """Build the canonical object key for a stored artefact.

    The investigation id is the first path segment, which lets the Supabase
    storage policies scope access by folder.
    """
    safe_name = os.path.basename(filename).replace("\\", "_").replace("/", "_")
    parts = [bucket, str(investigation_id)]
    if subdir:
        parts.append(subdir.strip("/"))
    parts.append(safe_name)
    return "/".join(parts)


class StorageBackend(ABC):
    """Common storage interface."""

    @abstractmethod
    def put(self, bucket: str, key: str, data: bytes) -> str: ...

    @abstractmethod
    def put_file(self, bucket: str, key: str, source: Path) -> str: ...

    @abstractmethod
    def get(self, bucket: str, key: str) -> bytes: ...

    @abstractmethod
    def open(self, bucket: str, key: str) -> BinaryIO: ...

    @abstractmethod
    def exists(self, bucket: str, key: str) -> bool: ...

    @abstractmethod
    def delete(self, bucket: str, key: str) -> None: ...

    @abstractmethod
    def path_for(self, bucket: str, key: str) -> Optional[Path]: ...


class LocalStorageBackend(StorageBackend):
    """Filesystem-backed storage rooted at `UPLOAD_DIRECTORY`."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        for bucket in (BUCKET_ORIGINALS, BUCKET_DERIVED, BUCKET_REPORTS):
            (self.root / bucket).mkdir(parents=True, exist_ok=True)

    def _resolve(self, bucket: str, key: str) -> Path:
        target = (self.root / bucket / key).resolve()
        bucket_root = (self.root / bucket).resolve()
        # Guard against path traversal out of the bucket.
        if not str(target).startswith(str(bucket_root)):
            raise StorageError(f"Refusing to access '{key}' outside bucket '{bucket}'")
        return target

    def put(self, bucket: str, key: str, data: bytes) -> str:
        target = self._resolve(bucket, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return str(target)

    def put_file(self, bucket: str, key: str, source: Path) -> str:
        target = self._resolve(bucket, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return str(target)

    def get(self, bucket: str, key: str) -> bytes:
        target = self._resolve(bucket, key)
        if not target.exists():
            raise StorageError(f"Object '{key}' does not exist in '{bucket}'")
        return target.read_bytes()

    def open(self, bucket: str, key: str) -> BinaryIO:
        target = self._resolve(bucket, key)
        if not target.exists():
            raise StorageError(f"Object '{key}' does not exist in '{bucket}'")
        return open(target, "rb")

    def exists(self, bucket: str, key: str) -> bool:
        try:
            return self._resolve(bucket, key).exists()
        except StorageError:
            return False

    def delete(self, bucket: str, key: str) -> None:
        if bucket in IMMUTABLE_BUCKETS:
            raise StorageError(f"Bucket '{bucket}' is immutable and cannot be modified")
        target = self._resolve(bucket, key)
        if target.exists():
            target.unlink()

    def path_for(self, bucket: str, key: str) -> Optional[Path]:
        try:
            target = self._resolve(bucket, key)
        except StorageError:
            return None
        return target if target.exists() else None


class SupabaseStorageBackend(StorageBackend):
    """Supabase Storage backend, used when the deployment targets the cloud."""

    def __init__(self, url: str, service_role_key: str):
        from supabase import create_client  # imported lazily

        self.client = create_client(url, service_role_key)
        self.url = url

    def put(self, bucket: str, key: str, data: bytes) -> str:
        self.client.storage.from_(bucket).upload(key, data, upsert=False)
        return f"{bucket}/{key}"

    def put_file(self, bucket: str, key: str, source: Path) -> str:
        return self.put(bucket, key, source.read_bytes())

    def get(self, bucket: str, key: str) -> bytes:
        data = self.client.storage.from_(bucket).download(key)
        return bytes(data)

    def open(self, bucket: str, key: str) -> BinaryIO:
        import io

        return io.BytesIO(self.get(bucket, key))

    def exists(self, bucket: str, key: str) -> bool:
        try:
            self.client.storage.from_(bucket).download(key)
            return True
        except Exception:
            return False

    def delete(self, bucket: str, key: str) -> None:
        if bucket in IMMUTABLE_BUCKETS:
            raise StorageError(f"Bucket '{bucket}' is immutable and cannot be modified")
        self.client.storage.from_(bucket).remove([key])

    def path_for(self, bucket: str, key: str) -> Optional[Path]:
        return None

    def signed_url(self, bucket: str, key: str, expires_in: int = 900) -> str:
        return self.client.storage.from_(bucket).create_signed_url(key, expires_in)


_backend: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Return the configured storage backend."""
    global _backend
    if _backend is None:
        if settings.uses_supabase_storage:
            try:
                _backend = SupabaseStorageBackend(
                    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
                )
                logger.info("Using Supabase Storage backend")
            except Exception:
                logger.exception(
                    "Supabase Storage is configured but unavailable; falling back to local storage"
                )
                _backend = LocalStorageBackend(settings.storage_root)
        else:
            _backend = LocalStorageBackend(settings.storage_root)
            logger.info("Using local storage backend at %s", settings.storage_root)
    return _backend


def reset_storage() -> None:
    """Drop the cached backend (used by tests)."""
    global _backend
    _backend = None


# -----------------------------------------------------------------------------
# Download authorisation
# -----------------------------------------------------------------------------
def signed_download_token(bucket: str, key: str, expires_minutes: int = 15) -> str:
    """Create a short-lived token authorising a direct download."""
    expiry = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = f"{bucket}|{key}|{expiry.timestamp()}"
    signature = sha256_text(payload + settings.APP_SECRET_KEY)
    return f"{expiry.timestamp()}.{signature}"


def verify_download_token(bucket: str, key: str, token: str) -> bool:
    """Validate a token produced by `signed_download_token`."""
    try:
        expiry_raw, signature = token.split(".", 1)
        expiry = float(expiry_raw)
    except (ValueError, AttributeError):
        return False

    if datetime.now(timezone.utc).timestamp() > expiry:
        return False

    payload = f"{bucket}|{key}|{expiry}"
    expected = sha256_text(payload + settings.APP_SECRET_KEY)
    return constant_time_equals(signature, expected)


def guess_mime_type(filename: str) -> str:
    """Best-effort MIME type for a filename."""
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"

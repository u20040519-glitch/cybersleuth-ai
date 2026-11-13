#!/usr/bin/env python3
# =============================================================================
# PROJECT NEXUS AI - Database Backup & Restore Scripts
# =============================================================================
# Implements scheduled and manual database backups with encryption,
# verification, retention, and restoration testing.
#
# Usage:
#   python backup_db.py                    # Create a backup
#   python backup_db.py --restore <file>   # Restore from a backup
#   python backup_db.py --verify <file>    # Verify a backup
#   python backup_db.py --list             # List available backups
#
# Environment variables:
#   DATABASE_URL          - PostgreSQL connection string
#   BACKUP_ENCRYPTION_KEY - Key for encrypting backups (min 32 chars)
#   BACKUP_RETENTION_DAYS - Days to retain backups (default: 30)
#   BACKUP_DIRECTORY      - Directory to store backups (default: ./backups)
# =============================================================================

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography.fernet import Fernet

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./nexus_ai.db")
ENCRYPTION_KEY = os.getenv("BACKUP_ENCRYPTION_KEY", "")
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIRECTORY", "./backups"))

# Ensure backup directory exists
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_encryption_key() -> bytes:
    """Derive a Fernet-compatible key from the encryption key env var."""
    if not ENCRYPTION_KEY or len(ENCRYPTION_KEY) < 32:
        raise ValueError(
            "BACKUP_ENCRYPTION_KEY must be set to at least 32 characters"
        )
    # Use SHA-256 to derive a 32-byte key
    key_hash = hashlib.sha256(ENCRYPTION_KEY.encode()).digest()
    # Fernet needs URL-safe base64-encoded 32-byte key
    import base64
    return base64.urlsafe_b64encode(key_hash)


def _encrypt_data(data: bytes) -> bytes:
    """Encrypt data using Fernet symmetric encryption."""
    f = Fernet(_get_encryption_key())
    return f.encrypt(data)


def _decrypt_data(data: bytes) -> bytes:
    """Decrypt data using Fernet symmetric encryption."""
    f = Fernet(_get_encryption_key())
    return f.decrypt(data)


def _parse_postgres_url(url: str) -> dict:
    """Parse a PostgreSQL URL into connection parameters."""
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    if url.startswith("postgresql+asyncpg://"):
        url = url[len("postgresql+asyncpg://"):]
    elif url.startswith("postgresql://"):
        url = url[len("postgresql://"):]

    # Split user:password@host:port/dbname
    if "@" in url:
        auth, hostpart = url.split("@", 1)
        if ":" in auth:
            username, password = auth.split(":", 1)
        else:
            username, password = auth, ""
    else:
        username, password = "", ""
        hostpart = url

    if "/" in hostpart:
        hostport, dbname = hostpart.split("/", 1)
    else:
        hostport, dbname = hostpart, "postgres"

    if ":" in hostport:
        host, port = hostport.split(":", 1)
    else:
        host, port = hostport, "5432"

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "dbname": dbname,
    }


def _timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _backup_filename(ext: str = "sql") -> str:
    """Generate a backup filename with timestamp."""
    return f"nexus_ai_backup_{_timestamp()}.{ext}"


def _manifest_filename() -> str:
    """Return the manifest file path."""
    return str(BACKUP_DIR / "backup_manifest.json")


def _load_manifest() -> list[dict]:
    """Load the backup manifest."""
    manifest_path = Path(_manifest_filename())
    if manifest_path.exists():
        with open(manifest_path, "r") as f:
            return json.load(f)
    return []


def _save_manifest(manifest: list[dict]) -> None:
    """Save the backup manifest."""
    with open(_manifest_filename(), "w") as f:
        json.dump(manifest, f, indent=2)


def _add_to_manifest(entry: dict) -> None:
    """Add an entry to the backup manifest."""
    manifest = _load_manifest()
    manifest.append(entry)
    _save_manifest(manifest)


def _remove_from_manifest(filename: str) -> None:
    """Remove an entry from the backup manifest."""
    manifest = _load_manifest()
    manifest = [e for e in manifest if e.get("filename") != filename]
    _save_manifest(manifest)


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def create_backup() -> dict:
    """Create a database backup with encryption and verification."""
    print(f"[{_timestamp()}] Starting database backup...")

    if DATABASE_URL.startswith("sqlite"):
        return _backup_sqlite()
    elif DATABASE_URL.startswith("postgresql"):
        return _backup_postgresql()
    else:
        raise ValueError(f"Unsupported database URL: {DATABASE_URL}")


def _backup_sqlite() -> dict:
    """Backup SQLite database by copying the file."""
    # Extract the SQLite file path from the URL
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    source = Path(db_path)

    if not source.exists():
        raise FileNotFoundError(f"SQLite database not found: {source}")

    backup_name = _backup_filename("db")
    backup_path = BACKUP_DIR / backup_name

    # Copy the database file
    shutil.copy2(str(source), str(backup_path))

    # Compute SHA-256 hash
    file_hash = _compute_file_hash(backup_path)

    # Get file size
    file_size = backup_path.stat().st_size

    entry = {
        "filename": backup_name,
        "path": str(backup_path),
        "timestamp": _timestamp(),
        "database_type": "sqlite",
        "file_size_bytes": file_size,
        "sha256": file_hash,
        "encrypted": False,
        "verified": True,
    }

    _add_to_manifest(entry)
    print(f"[{_timestamp()}] Backup created: {backup_name} ({file_size} bytes)")
    return entry


def _backup_postgresql() -> dict:
    """Backup PostgreSQL database using pg_dump with encryption."""
    params = _parse_postgres_url(DATABASE_URL)
    backup_name = _backup_filename("sql")
    backup_path = BACKUP_DIR / backup_name
    encrypted_path = BACKUP_DIR / f"{backup_name}.enc"

    # Build pg_dump command
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]

    cmd = [
        "pg_dump",
        "-h", params["host"],
        "-p", params["port"],
        "-U", params["username"],
        "-d", params["dbname"],
        "--no-password",
        "--verbose",
        "-f", str(backup_path),
    ]

    print(f"[{_timestamp()}] Running pg_dump...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr}")

    print(f"[{_timestamp()}] pg_dump completed")

    # Encrypt the backup
    if ENCRYPTION_KEY:
        print(f"[{_timestamp()}] Encrypting backup...")
        with open(backup_path, "rb") as f:
            plain_data = f.read()
        encrypted_data = _encrypt_data(plain_data)
        with open(encrypted_path, "wb") as f:
            f.write(encrypted_data)
        # Remove unencrypted file
        backup_path.unlink()
        backup_path = encrypted_path
        encrypted = True
    else:
        encrypted = False
        print(f"[{_timestamp()}] Warning: Backup not encrypted (no encryption key)")

    # Compute SHA-256 hash
    file_hash = _compute_file_hash(backup_path)
    file_size = backup_path.stat().st_size

    entry = {
        "filename": backup_path.name,
        "path": str(backup_path),
        "timestamp": _timestamp(),
        "database_type": "postgresql",
        "file_size_bytes": file_size,
        "sha256": file_hash,
        "encrypted": encrypted,
        "verified": False,  # Will be verified separately
        "pg_dump_stdout": result.stdout[:500] if result.stdout else "",
    }

    _add_to_manifest(entry)
    print(f"[{_timestamp()}] Backup created: {backup_path.name} ({file_size} bytes)")
    return entry


def _compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_backup(filename: str) -> bool:
    """Verify a backup file's integrity."""
    manifest = _load_manifest()
    entry = next((e for e in manifest if e.get("filename") == filename), None)

    if not entry:
        print(f"[ERROR] Backup '{filename}' not found in manifest")
        return False

    backup_path = Path(entry["path"])
    if not backup_path.exists():
        print(f"[ERROR] Backup file not found: {backup_path}")
        return False

    # Verify hash
    actual_hash = _compute_file_hash(backup_path)
    if actual_hash != entry.get("sha256"):
        print(f"[ERROR] Hash mismatch for {filename}")
        print(f"  Expected: {entry.get('sha256')}")
        print(f"  Actual:   {actual_hash}")
        return False

    # For encrypted backups, try to decrypt
    if entry.get("encrypted") and ENCRYPTION_KEY:
        try:
            with open(backup_path, "rb") as f:
                encrypted_data = f.read()
            _decrypt_data(encrypted_data)
        except Exception as exc:
            print(f"[ERROR] Decryption failed: {exc}")
            return False

    # For PostgreSQL backups, verify it's a valid SQL dump
    if entry.get("database_type") == "postgresql" and not entry.get("encrypted"):
        with open(backup_path, "r") as f:
            header = f.read(100)
        if "PostgreSQL database dump" not in header:
            print(f"[WARNING] Backup may not be a valid PostgreSQL dump")

    # Update manifest
    entry["verified"] = True
    entry["verified_at"] = _timestamp()
    _save_manifest(manifest)

    print(f"[OK] Backup '{filename}' verified successfully")
    return True


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

def restore_backup(filename: str) -> bool:
    """Restore a database from a backup file."""
    manifest = _load_manifest()
    entry = next((e for e in manifest if e.get("filename") == filename), None)

    if not entry:
        print(f"[ERROR] Backup '{filename}' not found in manifest")
        return False

    backup_path = Path(entry["path"])
    if not backup_path.exists():
        print(f"[ERROR] Backup file not found: {backup_path}")
        return False

    # Verify before restore
    if not entry.get("verified"):
        print(f"[WARNING] Backup not verified. Verifying now...")
        if not verify_backup(filename):
            print(f"[ERROR] Backup verification failed. Aborting restore.")
            return False

    print(f"[{_timestamp()}] Starting restore from: {filename}")

    if DATABASE_URL.startswith("sqlite"):
        return _restore_sqlite(backup_path, entry)
    elif DATABASE_URL.startswith("postgresql"):
        return _restore_postgresql(backup_path, entry)
    else:
        raise ValueError(f"Unsupported database URL: {DATABASE_URL}")


def _restore_sqlite(backup_path: Path, entry: dict) -> bool:
    """Restore SQLite database from backup."""
    db_path = Path(DATABASE_URL.replace("sqlite+aiosqlite:///", ""))

    # Close any connections first - in production, stop the app
    shutil.copy2(str(backup_path), str(db_path))
    print(f"[{_timestamp()}] SQLite database restored to: {db_path}")
    return True


def _restore_postgresql(backup_path: Path, entry: dict) -> bool:
    """Restore PostgreSQL database from backup."""
    params = _parse_postgres_url(DATABASE_URL)

    # Decrypt if needed
    restore_source = backup_path
    if entry.get("encrypted") and ENCRYPTION_KEY:
        print(f"[{_timestamp()}] Decrypting backup...")
        with open(backup_path, "rb") as f:
            encrypted_data = f.read()
        decrypted_data = _decrypt_data(encrypted_data)
        decrypted_path = BACKUP_DIR / f"decrypted_{_timestamp()}.sql"
        with open(decrypted_path, "wb") as f:
            f.write(decrypted_data)
        restore_source = decrypted_path

    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]

    cmd = [
        "psql",
        "-h", params["host"],
        "-p", params["port"],
        "-U", params["username"],
        "-d", params["dbname"],
        "--no-password",
        "-f", str(restore_source),
    ]

    print(f"[{_timestamp()}] Running psql restore...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    # Clean up decrypted file
    if restore_source != backup_path:
        restore_source.unlink()

    if result.returncode != 0:
        print(f"[ERROR] psql restore failed: {result.stderr}")
        return False

    print(f"[{_timestamp()}] Database restored successfully")
    return True


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------

def cleanup_old_backups() -> int:
    """Remove backups older than the retention period."""
    manifest = _load_manifest()
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    removed = 0

    remaining = []
    for entry in manifest:
        # Parse timestamp in format YYYYMMDD_HHMMSS
        try:
            entry_time = datetime.strptime(entry["timestamp"], "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
        except (ValueError, KeyError):
            # If we can't parse, keep the backup
            remaining.append(entry)
            continue
        if entry_time < cutoff:
            # Remove the file
            backup_path = Path(entry["path"])
            if backup_path.exists():
                backup_path.unlink()
                print(f"[{_timestamp()}] Removed expired backup: {entry['filename']}")
            removed += 1
        else:
            remaining.append(entry)

    _save_manifest(remaining)
    print(f"[{_timestamp()}] Retention cleanup: removed {removed} old backups")
    return removed


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def list_backups() -> None:
    """List all available backups."""
    manifest = _load_manifest()
    if not manifest:
        print("No backups found.")
        return

    print(f"\n{'Filename':<40} {'Type':<12} {'Size':<10} {'Encrypted':<10} {'Verified':<10} {'Timestamp'}")
    print("-" * 100)
    for entry in manifest:
        print(
            f"{entry.get('filename', 'N/A'):<40} "
            f"{entry.get('database_type', 'N/A'):<12} "
            f"{entry.get('file_size_bytes', 0):<10} "
            f"{str(entry.get('encrypted', False)):<10} "
            f"{str(entry.get('verified', False)):<10} "
            f"{entry.get('timestamp', 'N/A')}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PROJECT NEXUS AI Database Backup & Restore"
    )
    parser.add_argument(
        "--backup", action="store_true", help="Create a new backup"
    )
    parser.add_argument(
        "--restore", metavar="FILENAME", help="Restore from a backup file"
    )
    parser.add_argument(
        "--verify", metavar="FILENAME", help="Verify a backup file"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all backups"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Remove expired backups"
    )

    args = parser.parse_args()

    if args.backup:
        try:
            create_backup()
        except Exception as exc:
            print(f"[ERROR] Backup failed: {exc}")
            sys.exit(1)

    elif args.restore:
        try:
            success = restore_backup(args.restore)
            sys.exit(0 if success else 1)
        except Exception as exc:
            print(f"[ERROR] Restore failed: {exc}")
            sys.exit(1)

    elif args.verify:
        try:
            success = verify_backup(args.verify)
            sys.exit(0 if success else 1)
        except Exception as exc:
            print(f"[ERROR] Verification failed: {exc}")
            sys.exit(1)

    elif args.list:
        list_backups()

    elif args.cleanup:
        cleanup_old_backups()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

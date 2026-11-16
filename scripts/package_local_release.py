# =============================================================================
# CYBERSLEUTH AI - Package the local release
# =============================================================================
# Packs the project into a ZIP that can be copied to another machine:
#
#   * every file that is tracked by git (so no secrets: the .env files are
#     gitignored and therefore never part of the archive),
#   * the built frontend (frontend/dist), when it is present, so the app can
#     be served immediately without an npm install.
#
# Usage:
#   python scripts/package_local_release.py [--output <path>]
# =============================================================================

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "cybersleuth-ai-local.zip"

# Directories that are added on top of the tracked files.
EXTRA_DIRECTORIES = ["frontend/dist"]


def tracked_files() -> list[str]:
    """Every file tracked by git, relative to the repository root."""
    output = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"], text=False
    )
    return [name for name in output.decode("utf-8").split("\0") if name]


def extra_files() -> list[str]:
    """Files that are not tracked by git but belong in the archive."""
    collected: list[str] = []
    for directory in EXTRA_DIRECTORIES:
        base = REPO_ROOT / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                collected.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
    return collected


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the local release.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output = Path(args.output).resolve()
    files = sorted(set(tracked_files()) | set(extra_files()))

    missing = [name for name in files if not (REPO_ROOT / name).exists()]
    if missing:
        print(f"Skipping {len(missing)} file(s) that are not on disk:", file=sys.stderr)
        for name in missing[:10]:
            print(f"  {name}", file=sys.stderr)

    written = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            path = REPO_ROOT / name
            if not path.is_file():
                continue
            archive.write(path, arcname=name)
            written += 1

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Wrote {written} files to {output} ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

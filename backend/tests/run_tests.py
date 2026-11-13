# =============================================================================
# PROJECT NEXUS AI - Test Runner Script
# =============================================================================
# Run all security and privacy tests.
# Usage: python run_tests.py
# =============================================================================

import subprocess
import sys
from pathlib import Path


def main():
    test_dir = Path(__file__).parent
    test_files = [
        "test_auth.py",
        "test_authorization.py",
        "test_privacy.py",
        "test_security.py",
        "test_operations.py",
        "test_accessibility.py",
    ]

    print("=" * 60)
    print("PROJECT NEXUS AI - Security & Privacy Test Suite")
    print("=" * 60)

    all_passed = True
    for test_file in test_files:
        test_path = test_dir / test_file
        if not test_path.exists():
            print(f"\n[SKIP] {test_file} - not found")
            continue

        print(f"\n[RUN] {test_file}")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"[PASS] {test_file}")
        else:
            print(f"[FAIL] {test_file}")
            all_passed = False
            # Print last 20 lines of output
            lines = result.stdout.split("\n")[-20:]
            for line in lines:
                if line.strip():
                    print(f"  {line}")

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

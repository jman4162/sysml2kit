"""Validate writer-emitted .sysml fixtures against the OMG pilot implementation.

Downloads the pilot-implementation jar (EPL-2.0) into a local cache at run
time — it is never committed to this Apache-2.0 repository — and runs it out
of process on every ``.sysml`` file under ``tests/fixtures``. Exits non-zero
if the pilot rejects any file.

The jar coordinates track the spec release pinned in SPEC.md (2026-05).
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(__file__).resolve().parent / ".cache"
FIXTURES = ROOT / "tests" / "fixtures"

# Set to the validator artifact published with the pinned SysML-v2-Release
# train (see SPEC.md). Left empty until the coordinate is verified against the
# release assets; the script fails loudly rather than guessing a URL.
JAR_URL = ""


def fetch_jar() -> Path:
    """Download the validator jar into the cache if it is not already there."""
    if not JAR_URL:
        print(
            "[oracle] JAR_URL is not set. Pin the validator artifact from the "
            "SysML-v2-Release train (SPEC.md) before running the oracle.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    CACHE.mkdir(exist_ok=True)
    jar = CACHE / JAR_URL.rsplit("/", 1)[-1]
    if not jar.exists():
        import urllib.request

        print(f"[oracle] downloading {JAR_URL}")
        urllib.request.urlretrieve(JAR_URL, jar)
    return jar


def main() -> int:
    """Run the pilot validator over every fixture; return a process exit code."""
    files = sorted(FIXTURES.glob("**/*.sysml")) if FIXTURES.exists() else []
    if not files:
        print("[oracle] no .sysml fixtures yet; nothing to validate")
        return 0
    jar = fetch_jar()
    failures = 0
    for f in files:
        proc = subprocess.run(
            ["java", "-jar", str(jar), str(f)],
            capture_output=True,
            text=True,
            check=False,
        )
        status = "ok" if proc.returncode == 0 else "REJECTED"
        print(f"[oracle] {f.relative_to(ROOT)}: {status}")
        if proc.returncode != 0:
            failures += 1
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
    print(f"[oracle] {len(files)} file(s), {failures} rejected")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

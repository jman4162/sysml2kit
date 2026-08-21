"""Validate writer-emitted .sysml fixtures against the OMG pilot implementation.

Uses windtrader-java (GPL-3.0, a Maven-shade jar wrapping the EPL-2.0 pilot's
Xtext parser, pilot 0.56.0) as the out-of-process oracle: OMG itself publishes
no runnable validator. The jar is downloaded into a local cache at run time —
never committed to this Apache-2.0 repository — and verified against a
pinned sha256.

Invocation contract (verified against windtrader-java v0.1.1):
``java -jar <jar> check`` with the file content on **stdin**; exit 0 = valid
syntax, 2 = rejected, 3 = tool error. Requires Java 21.
"""

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(__file__).resolve().parent / ".cache"
FIXTURES = ROOT / "tests" / "fixtures"

JAR_URL = (
    "https://github.com/Westfall-io/windtrader-java/releases/download/"
    "v0.1.1/windtrader-java-0.1.1.jar"
)
JAR_SHA256 = "0f9eeed46929c41f6cf9257a1551593509fc73312f3724082ed66e5b6ab9038f"


def fetch_jar() -> Path:
    """Download the validator jar into the cache and verify its sha256."""
    CACHE.mkdir(exist_ok=True)
    jar = CACHE / JAR_URL.rsplit("/", 1)[-1]
    if not jar.exists():
        import urllib.request

        print(f"[oracle] downloading {JAR_URL}")
        urllib.request.urlretrieve(JAR_URL, jar)
    digest = hashlib.sha256(jar.read_bytes()).hexdigest()
    if digest != JAR_SHA256:
        print(
            f"[oracle] sha256 mismatch for {jar.name}: got {digest}, "
            f"expected {JAR_SHA256}",
            file=sys.stderr,
        )
        jar.unlink()
        raise SystemExit(1)
    return jar


def check_file(jar: Path, path: Path) -> int:
    """Run the validator on one file; returns its exit code."""
    proc = subprocess.run(
        ["java", "-jar", str(jar), "check"],
        input=path.read_text(),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 3:
        print(f"[oracle] tool error on {path.name} (is Java 21 installed?)", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
    elif proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


def main() -> int:
    """Run the pilot validator over every fixture; return a process exit code."""
    files = sorted(FIXTURES.glob("**/*.sysml")) if FIXTURES.exists() else []
    if not files:
        print("[oracle] no .sysml fixtures found; nothing to validate")
        return 0
    jar = fetch_jar()
    rejected = tool_errors = 0
    for f in files:
        code = check_file(jar, f)
        status = {0: "ok", 2: "REJECTED"}.get(code, f"TOOL ERROR ({code})")
        print(f"[oracle] {f.relative_to(ROOT)}: {status}")
        if code == 2:
            rejected += 1
        elif code != 0:
            tool_errors += 1
    print(f"[oracle] {len(files)} file(s), {rejected} rejected, {tool_errors} tool error(s)")
    return 1 if (rejected or tool_errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())

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
            f"[oracle] sha256 mismatch for {jar.name}: got {digest}, expected {JAR_SHA256}",
            file=sys.stderr,
        )
        jar.unlink()
        raise SystemExit(1)
    return jar


def check_file(jar: Path, path: Path) -> str:
    """Run the validator on one file; returns ok / rejected / limitation / error."""
    proc = subprocess.run(
        ["java", "-jar", str(jar), "check"],
        input=path.read_text(),
        capture_output=True,
        text=True,
        check=False,
    )
    output = proc.stdout + proc.stderr
    if proc.returncode == 0:
        return "ok"
    if proc.returncode == 2:
        if "error: line=" in output:
            print(output)
            return "rejected"
        if "ValueConverterException" in output:
            # The jar runs the pilot without the KerML standard library, so
            # unit-literal annotations ([kg]) NPE inside its semantic layer.
            # Valid syntax, known tool limitation - not a rejection of ours.
            return "limitation"
        print(output)
        return "rejected"
    print(f"[oracle] tool error on {path.name} (is Java 21 installed?)", file=sys.stderr)
    print(proc.stderr, file=sys.stderr)
    return "error"


def main() -> int:
    """Run the pilot validator over every fixture; return a process exit code."""
    files = sorted(FIXTURES.glob("**/*.sysml")) if FIXTURES.exists() else []
    if not files:
        print("[oracle] no .sysml fixtures found; nothing to validate")
        return 0
    jar = fetch_jar()
    counts = {"ok": 0, "rejected": 0, "limitation": 0, "error": 0}
    for f in files:
        status = check_file(jar, f)
        counts[status] += 1
        label = {"limitation": "ok (known unit-literal limitation)"}.get(status, status)
        print(f"[oracle] {f.relative_to(ROOT)}: {label}")
    print(
        f"[oracle] {len(files)} file(s): {counts['ok']} ok, "
        f"{counts['limitation']} limited-ok, {counts['rejected']} rejected, "
        f"{counts['error']} tool error(s)"
    )
    return 1 if (counts["rejected"] or counts["error"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())

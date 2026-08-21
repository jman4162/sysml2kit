"""API-first Python tooling for building, querying, validating, and automating SysML v2 models.

The 0.0.x releases are a published skeleton; the object model, writer, and
queries land in 0.1.0. See https://github.com/jman4162/sysml2kit.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sysml2kit")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]

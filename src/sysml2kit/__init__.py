"""API-first Python tooling for building, querying, validating, and automating SysML v2 models.

See https://github.com/jman4162/sysml2kit and SPEC.md for the element subset
(the "pragmatic profile") and the pinned spec release.
"""

from importlib.metadata import PackageNotFoundError, version

from sysml2kit.model import Model, builder

try:
    __version__ = version("sysml2kit")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0.dev0"

__all__ = ["Model", "__version__", "builder"]

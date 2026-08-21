"""Parser backends.

The registry is a plain dict for now; the ``sysml2kit.backends`` entry-point
group name is reserved for external backends (JVM pilot wrapper, API-based,
proprietary tools) once someone needs one.
"""

from __future__ import annotations

from sysml2kit.backends.protocol import ParseError, ParserBackend


def _make_sysmlpy() -> ParserBackend:
    from sysml2kit.backends.sysmlpy import SysmlpyBackend

    return SysmlpyBackend()


_FACTORIES = {
    "sysmlpy": _make_sysmlpy,
}


def get_backend(name: str = "sysmlpy") -> ParserBackend:
    """Return a parser backend by name; raises KeyError for unknown names."""
    if name not in _FACTORIES:
        raise KeyError(f"unknown backend {name!r}; available: {sorted(_FACTORIES)}")
    return _FACTORIES[name]()


__all__ = ["ParseError", "ParserBackend", "get_backend"]

"""The verification engine registry.

Engines are callables taking one payload dict and returning a flat metrics
mapping. Models refer to engines **by name only**; names resolve against
this registry, populated from the ``sysml2kit.engines`` entry-point group
(packages opt in) and from explicit ``register`` calls (operator input).
Model text never names importable code paths.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from importlib import metadata
from typing import Any, Self

Engine = Callable[[dict[str, Any]], Mapping[str, float | int | str | bool | None]]

ENTRY_POINT_GROUP = "sysml2kit.engines"


class EngineNotFoundError(KeyError):
    """Raised when a binding names an engine the registry does not have."""

    def __init__(self, name: str, available: list[str]) -> None:
        listing = ", ".join(sorted(available)) or "(none)"
        super().__init__(f"no engine named {name!r}; available: {listing}")
        self.engine_name = name


class EngineRegistry:
    """Named verification engines, lazily loaded."""

    def __init__(self) -> None:
        self._engines: dict[str, Engine] = {}
        self._pending: dict[str, metadata.EntryPoint] = {}
        self._dists: dict[str, str | None] = {}

    @classmethod
    def discover(cls) -> Self:
        """Build a registry from the ``sysml2kit.engines`` entry-point group.

        Entry points are recorded without loading; a broken engine only fails
        when it is actually requested.
        """
        registry = cls()
        for entry_point in metadata.entry_points(group=ENTRY_POINT_GROUP):
            registry._pending[entry_point.name] = entry_point
            dist = getattr(entry_point, "dist", None)
            registry._dists[entry_point.name] = dist.name if dist is not None else None
        return registry

    def register(self, name: str, engine: Engine, *, dist: str | None = None) -> None:
        """Register an engine under a name (overrides an entry point of the same name)."""
        self._engines[name] = engine
        self._dists[name] = dist

    def get(self, name: str) -> Engine:
        """Return the engine, loading its entry point on first use."""
        if name in self._engines:
            return self._engines[name]
        if name in self._pending:
            from typing import cast

            engine = cast(Engine, self._pending.pop(name).load())
            self._engines[name] = engine
            return engine
        raise EngineNotFoundError(name, self.names())

    def names(self) -> list[str]:
        """All registered and discoverable engine names."""
        return sorted(set(self._engines) | set(self._pending))

    def version_of(self, name: str) -> str:
        """Version of the distribution providing an engine, or 'unknown'."""
        dist = self._dists.get(name)
        if dist is None:
            return "unknown"
        try:
            return metadata.version(dist)
        except metadata.PackageNotFoundError:
            return "unknown"

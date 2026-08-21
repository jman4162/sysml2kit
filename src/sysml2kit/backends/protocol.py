"""The parser-backend protocol.

sysml2kit does not implement the SysML v2 grammar; reading textual notation
goes through a backend implementing this protocol. The shipped backend wraps
sysmlpy (behind the ``parse`` extra); a JVM- or API-based backend can slot in
without core changes.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from sysml2kit.model.container import Model


class ParseError(ValueError):
    """Raised when a backend rejects the input text."""

    def __init__(self, message: str, *, filename: str | None = None) -> None:
        super().__init__(message if filename is None else f"{filename}: {message}")
        self.filename = filename


@runtime_checkable
class ParserBackend(Protocol):
    """Anything that can turn SysML v2 text into a sysml2kit Model."""

    name: str

    def parse(self, text: str, *, filename: str | None = None) -> Model:
        """Parse one unit of textual notation."""
        ...

    def parse_files(self, paths: Sequence[Path]) -> Model:
        """Parse several files into one model."""
        ...

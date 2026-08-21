"""Attribute values with units and provenance.

Follows the ``Assumption`` pattern from spacedc-mdao: a number in a model
should say where it came from. Units are stored as text (what the textual
notation carries, e.g. ``"dBW"``); ``sysml2kit.units`` checks them against
pint during validation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class AttributeValue(BaseModel):
    """A literal value with optional unit text and provenance."""

    model_config = ConfigDict(frozen=True)

    value: float | int | str | bool | None = None
    unit: str | None = None
    source: str | None = None
    confidence: Literal["low", "medium", "high"] | None = None

    def render(self) -> str:
        """Render as textual-notation value text, e.g. ``52.0 [dBW]``."""
        body = f'"{self.value}"' if isinstance(self.value, str) else str(self.value)
        if self.unit:
            return f"{body} [{self.unit}]"
        return body

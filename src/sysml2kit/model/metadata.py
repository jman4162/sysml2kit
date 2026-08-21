"""Metadata annotation elements."""

from __future__ import annotations

from pydantic import Field

from sysml2kit.model.base import Element, Ref


class MetadataDefinition(Element):
    """A reusable definition of a metadata annotation kind."""


class MetadataUsage(Element):
    """A metadata annotation on another element, as a key-value mapping."""

    definition: Ref | None = None
    annotated: Ref | None = None
    values: dict[str, str | float | int | bool] = Field(default_factory=dict)

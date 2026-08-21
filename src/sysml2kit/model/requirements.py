"""Requirement and constraint elements."""

from __future__ import annotations

from sysml2kit.model.base import Element, Ref


class RequirementDefinition(Element):
    """A reusable definition of a requirement kind."""


class RequirementUsage(Element):
    """A requirement occurrence with an optional subject and statement text."""

    definition: Ref | None = None
    subject: Ref | None = None
    text: str | None = None


class ConstraintUsage(Element):
    """A constraint; the expression is an opaque string in v0.1."""

    expression: str | None = None

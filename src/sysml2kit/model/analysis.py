"""Analysis case elements (stubs in v0.1: subject and objective, no actions)."""

from __future__ import annotations

from sysml2kit.model.base import Element, Ref


class AnalysisCaseDefinition(Element):
    """A reusable definition of an analysis to run against a subject."""


class AnalysisCaseUsage(Element):
    """An analysis occurrence with a subject and an objective statement."""

    definition: Ref | None = None
    subject: Ref | None = None
    objective: str | None = None

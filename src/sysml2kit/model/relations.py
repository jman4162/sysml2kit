"""Reified traceability relationships.

The spec models some of these as membership forms; sysml2kit reifies each as
a first-class relationship with ``source``/``target`` refs (a documented
deviation, see SPEC.md).
"""

from __future__ import annotations

from sysml2kit.model.base import Relationship


class SatisfyRelationship(Relationship):
    """``source`` (a part or design element) satisfies ``target`` (a requirement)."""


class VerifyRelationship(Relationship):
    """``source`` (an analysis or test case) verifies ``target`` (a requirement)."""


class DeriveRelationship(Relationship):
    """``source`` (a requirement) is derived from ``target`` (a requirement)."""


class AllocateRelationship(Relationship):
    """``source`` (a function or requirement) is allocated to ``target`` (a part)."""

"""The ``@type`` vocabulary mapping, pinned to SysML-v2-Release 2026-05.

This is the only module allowed to hard-code spec ``@type`` strings; spec
bumps start (and mostly end) here. The reified traceability relationships
serialize under the closest standard names with a simplified
``source``/``target`` structure — a documented deviation, see SPEC.md.
"""

from __future__ import annotations

from sysml2kit.model.analysis import AnalysisCaseDefinition, AnalysisCaseUsage
from sysml2kit.model.base import Element
from sysml2kit.model.metadata import MetadataDefinition, MetadataUsage
from sysml2kit.model.relations import (
    AllocateRelationship,
    DeriveRelationship,
    SatisfyRelationship,
    VerifyRelationship,
)
from sysml2kit.model.requirements import (
    ConstraintUsage,
    RequirementDefinition,
    RequirementUsage,
)
from sysml2kit.model.structure import (
    AttributeDefinition,
    AttributeUsage,
    ConnectionUsage,
    InterfaceDefinition,
    Package,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
)

#: Class -> interchange ``@type`` string.
CLASS_TO_TYPE: dict[type[Element], str] = {
    Package: "Package",
    PartDefinition: "PartDefinition",
    PartUsage: "PartUsage",
    PortDefinition: "PortDefinition",
    PortUsage: "PortUsage",
    InterfaceDefinition: "InterfaceDefinition",
    ConnectionUsage: "ConnectionUsage",
    AttributeDefinition: "AttributeDefinition",
    AttributeUsage: "AttributeUsage",
    RequirementDefinition: "RequirementDefinition",
    RequirementUsage: "RequirementUsage",
    ConstraintUsage: "ConstraintUsage",
    AnalysisCaseDefinition: "AnalysisCaseDefinition",
    AnalysisCaseUsage: "AnalysisCaseUsage",
    MetadataDefinition: "MetadataDefinition",
    MetadataUsage: "MetadataUsage",
    SatisfyRelationship: "SatisfyRequirementUsage",
    VerifyRelationship: "VerifyRequirementUsage",
    DeriveRelationship: "DeriveRequirementUsage",
    AllocateRelationship: "AllocationUsage",
}

#: Interchange ``@type`` string -> class (inverse of CLASS_TO_TYPE).
TYPE_TO_CLASS: dict[str, type[Element]] = {name: cls for cls, name in CLASS_TO_TYPE.items()}

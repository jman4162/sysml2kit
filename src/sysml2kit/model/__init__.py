"""The sysml2kit object model: the pragmatic profile plus the Model container."""

from sysml2kit.model.analysis import AnalysisCaseDefinition, AnalysisCaseUsage
from sysml2kit.model.base import Element, OpaqueElement, Ref, Relationship
from sysml2kit.model.container import STABLE_ID_NAMESPACE, Model
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
from sysml2kit.model.values import AttributeValue

__all__ = [
    "STABLE_ID_NAMESPACE",
    "AllocateRelationship",
    "AnalysisCaseDefinition",
    "AnalysisCaseUsage",
    "AttributeDefinition",
    "AttributeUsage",
    "AttributeValue",
    "ConnectionUsage",
    "ConstraintUsage",
    "DeriveRelationship",
    "Element",
    "InterfaceDefinition",
    "MetadataDefinition",
    "MetadataUsage",
    "Model",
    "OpaqueElement",
    "Package",
    "PartDefinition",
    "PartUsage",
    "PortDefinition",
    "PortUsage",
    "Ref",
    "Relationship",
    "RequirementDefinition",
    "RequirementUsage",
    "SatisfyRelationship",
    "VerifyRelationship",
]

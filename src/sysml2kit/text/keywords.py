"""Element-kind to textual-notation keyword mapping and name escaping."""

from __future__ import annotations

import re

from sysml2kit.model.analysis import AnalysisCaseDefinition, AnalysisCaseUsage
from sysml2kit.model.base import Element
from sysml2kit.model.metadata import MetadataDefinition
from sysml2kit.model.requirements import (
    ConstraintUsage,
    RequirementDefinition,
    RequirementUsage,
)
from sysml2kit.model.structure import (
    AttributeDefinition,
    AttributeUsage,
    InterfaceDefinition,
    Package,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
)

#: Declaration keyword per element class (relationships and connections are
#: rendered specially by the writer).
KEYWORDS: dict[type[Element], str] = {
    Package: "package",
    PartDefinition: "part def",
    PartUsage: "part",
    PortDefinition: "port def",
    PortUsage: "port",
    InterfaceDefinition: "interface def",
    AttributeDefinition: "attribute def",
    AttributeUsage: "attribute",
    RequirementDefinition: "requirement def",
    RequirementUsage: "requirement",
    ConstraintUsage: "constraint",
    AnalysisCaseDefinition: "analysis def",
    AnalysisCaseUsage: "analysis",
    MetadataDefinition: "metadata def",
}

_PLAIN_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def escape_name(name: str) -> str:
    """Quote a name that is not a plain identifier (``'name with spaces'``)."""
    if _PLAIN_NAME.match(name):
        return name
    return "'" + name.replace("'", "\\'") + "'"

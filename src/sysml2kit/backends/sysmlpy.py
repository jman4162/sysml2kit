"""The sysmlpy parse backend (``pip install sysml2kit[parse]``).

Maps sysmlpy's parse tree into the pragmatic profile by the grammar-node
class name. Constructs sysmlpy resolves but the profile lacks become
:class:`OpaqueElement` records, so nothing silently disappears. Fidelity
note: sysmlpy 0.36 does not surface typing, multiplicity, or attribute
values on its wrapper objects, so those fields come back empty from a parse;
names, kinds, docs, and ownership round-trip.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sysml2kit.model.analysis import AnalysisCaseDefinition, AnalysisCaseUsage
from sysml2kit.model.base import Element, OpaqueElement
from sysml2kit.model.container import Model
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

logger = logging.getLogger(__name__)

#: sysmlpy grammar-node class name -> profile class.
_GRAMMAR_MAP: dict[str, type[Element]] = {
    "PackageDeclaration": Package,
    "Package": Package,
    "PartDefinition": PartDefinition,
    "PartUsage": PartUsage,
    "PortDefinition": PortDefinition,
    "PortUsage": PortUsage,
    "InterfaceDefinition": InterfaceDefinition,
    "AttributeDefinition": AttributeDefinition,
    "AttributeUsage": AttributeUsage,
    "RequirementDefinition": RequirementDefinition,
    "RequirementUsage": RequirementUsage,
    "ConstraintUsage": ConstraintUsage,
    "AnalysisCaseDefinition": AnalysisCaseDefinition,
    "AnalysisCaseUsage": AnalysisCaseUsage,
    "ConnectionUsage": ConnectionUsage,
}


def _require_sysmlpy() -> Any:
    try:
        import sysmlpy
    except ImportError as exc:  # pragma: no cover - exercised via the error message test
        raise ImportError("parsing needs the 'parse' extra: pip install sysml2kit[parse]") from exc
    return sysmlpy


class SysmlpyBackend:
    """Parse SysML v2 text with sysmlpy and map it into a Model."""

    name = "sysmlpy"

    def parse(self, text: str, *, filename: str | None = None) -> Model:
        """Parse one unit of textual notation."""
        sysmlpy = _require_sysmlpy()
        from sysml2kit.backends.protocol import ParseError

        try:
            parsed = sysmlpy.loads(text)
        except sysmlpy.SysMLSyntaxError as exc:
            raise ParseError(str(exc), filename=filename) from exc

        model = Model()
        for pkg in parsed.packages:
            self._convert(model, pkg, owner=None)
        return model

    def parse_files(self, paths: Sequence[Path]) -> Model:
        """Parse several files into one model (each file's packages become roots)."""
        model = Model()
        for path in paths:
            parsed_model = self.parse(path.read_text(), filename=str(path))
            for root in list(parsed_model.roots):
                _graft(model, parsed_model, root, owner=None)
        return model

    def _convert(self, model: Model, node: Any, owner: Element | None) -> None:
        grammar_kind = type(getattr(node, "grammar", node)).__name__
        cls = _GRAMMAR_MAP.get(grammar_kind)
        name = getattr(node, "name", None)
        doc = getattr(node, "doc", None)
        if cls is None:
            wrapper_kind = type(node).__name__
            logger.warning("sysmlpy construct %s (%s) kept as opaque", grammar_kind, wrapper_kind)
            element: Element = OpaqueElement(
                declared_name=name, type_name=grammar_kind, raw={"wrapper": wrapper_kind}
            )
        else:
            element = cls(declared_name=name, doc=doc)
        model.add(element, owner=owner)
        for child in getattr(node, "children", []) or []:
            self._convert(model, child, owner=element)


def _graft(target: Model, source: Model, eid: Any, owner: Element | None) -> None:
    element = source.elements[eid]
    target.add(element, owner=owner)
    for child_id in source.owned.get(eid, []):
        _graft(target, source, child_id, owner=element)

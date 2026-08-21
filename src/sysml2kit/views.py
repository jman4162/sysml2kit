"""Mermaid diagram output.

Two views: the ownership tree (packages/parts/ports) and the traceability
graph (requirements, parts, analyses; satisfy/verify/derive/allocate edges).
Node ids derive from qualified names, so output is deterministic and diffs
cleanly. Both mkdocs-material and Claude artifacts render mermaid fences.
"""

from __future__ import annotations

import re

from sysml2kit.model.analysis import AnalysisCaseUsage
from sysml2kit.model.base import Element, Relationship
from sysml2kit.model.container import Model
from sysml2kit.model.relations import (
    AllocateRelationship,
    DeriveRelationship,
    SatisfyRelationship,
    VerifyRelationship,
)
from sysml2kit.model.requirements import RequirementUsage
from sysml2kit.model.structure import Package, PartUsage, PortUsage

_EDGE_STYLE: dict[type[Relationship], str] = {
    SatisfyRelationship: "-- satisfy -->",
    VerifyRelationship: "-. verify .->",
    DeriveRelationship: "-. derive .->",
    AllocateRelationship: "== allocate ==>",
}


def _node_id(model: Model, element: Element) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", model.qualified_name(element))


def _label(element: Element) -> str:
    text = element.declared_short_name or element.declared_name or "unnamed"
    return text.replace('"', "'")


def to_mermaid_tree(model: Model) -> str:
    """Render the package/part/port ownership tree as a mermaid flowchart."""
    lines = ["flowchart TD"]
    kinds = (Package, PartUsage, PortUsage)
    shapes = {Package: ('["{}"]', ""), PartUsage: ('("{}")', ""), PortUsage: ('(["{}"])', "")}
    included: set[str] = set()
    for element in model.iter_elements():
        if not isinstance(element, kinds):
            continue
        nid = _node_id(model, element)
        shape = shapes[type(element)][0]
        lines.append(f"    {nid}{shape.format(_label(element))}")
        included.add(element.element_id.hex)
        owner = model.owner_of(element)
        while owner is not None and not isinstance(owner, kinds):
            owner = model.owner_of(owner)
        if owner is not None:
            lines.append(f"    {_node_id(model, owner)} --> {nid}")
    return "\n".join(lines) + "\n"


def to_mermaid_trace(model: Model) -> str:
    """Render the requirement traceability graph as a mermaid flowchart."""
    lines = ["flowchart LR"]
    interesting: set[str] = set()
    edges: list[str] = []
    for element in model.elements.values():
        if not isinstance(element, Relationship) or type(element) not in _EDGE_STYLE:
            continue
        try:
            source = model.resolve(element.source)
            target = model.resolve(element.target)
        except KeyError:
            continue
        edges.append(
            f"    {_node_id(model, source)} {_EDGE_STYLE[type(element)]} {_node_id(model, target)}"
        )
        interesting.add(source.element_id.hex)
        interesting.add(target.element_id.hex)
    for element in model.iter_elements():
        if element.element_id.hex not in interesting:
            continue
        nid = _node_id(model, element)
        if isinstance(element, RequirementUsage):
            lines.append(f'    {nid}{{{{"{_label(element)}"}}}}')
        elif isinstance(element, AnalysisCaseUsage):
            lines.append(f'    {nid}[/"{_label(element)}"/]')
        else:
            lines.append(f'    {nid}("{_label(element)}")')
    lines.extend(edges)
    return "\n".join(lines) + "\n"

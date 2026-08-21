"""Deterministic SysML v2 textual notation writer.

Output order follows the ownership tree (insertion order), indentation is
four spaces, and values render as ``= 52.0 [dBW]``. Elements outside the
pragmatic profile (:class:`OpaqueElement`) emit a marker comment; the JSON
interchange is the lossless format.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sysml2kit.model.analysis import AnalysisCaseUsage
from sysml2kit.model.base import Element, OpaqueElement, Ref, Relationship
from sysml2kit.model.container import Model
from sysml2kit.model.metadata import MetadataUsage
from sysml2kit.model.relations import (
    AllocateRelationship,
    DeriveRelationship,
    SatisfyRelationship,
    VerifyRelationship,
)
from sysml2kit.model.requirements import ConstraintUsage, RequirementUsage
from sysml2kit.model.structure import (
    AttributeUsage,
    ConnectionUsage,
    Package,
    PartUsage,
    PortUsage,
)

from .keywords import KEYWORDS, escape_name

_INDENT = "    "

# satisfy and allocate have first-class textual forms; the grammar has no
# standalone derive/verify statement, so those emit as NAMED dependencies
# whose name prefix (verify_/derive_) lets the parser reify the right kind.
_DEPENDENCY_PREFIX: dict[type[Element], str] = {
    VerifyRelationship: "verify_",
    DeriveRelationship: "derive_",
}


def _dependency_names(model: Model) -> dict[UUID, str]:
    """Deterministic verify_N/derive_N names, in ownership order."""
    names: dict[UUID, str] = {}
    counters = {"verify_": 0, "derive_": 0}
    for element in model.iter_elements():
        prefix = _DEPENDENCY_PREFIX.get(type(element))
        if prefix is not None:
            counters[prefix] += 1
            names[element.element_id] = f"{prefix}{counters[prefix]}"
    return names


def write_model(model: Model) -> str:
    """Render every root element; one blank line between roots."""
    names = _dependency_names(model)
    chunks = [_render(model, model.elements[root], 0, names) for root in model.roots]
    return "\n".join(chunk for chunk in chunks if chunk) + "\n"


def write_package(model: Model, package: Element | UUID) -> str:
    """Render a single package subtree."""
    element = model.resolve(package) if isinstance(package, UUID) else package
    return _render(model, element, 0, _dependency_names(model)) + "\n"


def write_file(model: Model, path: str | Path) -> None:
    """Write the rendered model to a ``.sysml`` file."""
    Path(path).write_text(write_model(model))


def _name_of(model: Model, ref: Ref) -> str:
    element = model.resolve(ref)
    return escape_name(element.declared_name or element.declared_short_name or "unnamed")


def _relative_path(model: Model, scope: UUID | None, ref: Ref) -> str:
    """Dotted name path from the scope element down to the target, if nested."""
    element = model.resolve(ref)
    parts = [element.declared_name or "unnamed"]
    current = model.owner.get(element.element_id)
    while current is not None and current != scope:
        owner = model.elements[current]
        parts.append(owner.declared_name or "unnamed")
        current = model.owner.get(current)
    if current != scope:
        return escape_name(parts[0])
    return ".".join(escape_name(p) for p in reversed(parts))


def _doc_block(element: Element, indent: str) -> list[str]:
    if not element.doc:
        return []
    return [f"{indent}doc /* {element.doc} */"]


def _header(element: Element) -> str:
    keyword = KEYWORDS[type(element)]
    parts = [keyword]
    if element.declared_short_name:
        parts.append(f"<{escape_name(element.declared_short_name)}>")
    if element.declared_name:
        parts.append(escape_name(element.declared_name))
    return " ".join(parts)


def _render(model: Model, element: Element, depth: int, dep_names: dict[UUID, str]) -> str:
    indent = _INDENT * depth
    if isinstance(element, OpaqueElement):
        return f"{indent}// opaque element ({element.type_name}): {element.label}"
    if isinstance(element, Relationship):
        scope = model.owner.get(element.element_id)
        source = _relative_path(model, scope, element.source)
        target = _relative_path(model, scope, element.target)
        if isinstance(element, SatisfyRelationship):
            return f"{indent}satisfy {target} by {source};"
        if isinstance(element, AllocateRelationship):
            return f"{indent}allocate {source} to {target};"
        name = dep_names[element.element_id]
        return f"{indent}dependency {name} from {source} to {target};"
    if isinstance(element, ConnectionUsage):
        return _render_connection(model, element, indent)
    if isinstance(element, AttributeUsage):
        return _render_attribute(model, element, indent)
    if isinstance(element, MetadataUsage):
        return _render_metadata(model, element, indent)

    header = indent + _header(element)
    if isinstance(element, PartUsage | PortUsage | AnalysisCaseUsage) and element.definition:
        header += f" : {_name_of(model, element.definition)}"
    if isinstance(element, PartUsage) and element.multiplicity:
        header += f" {element.multiplicity}"
    if isinstance(element, Package) and element.imports:
        pass  # imports render inside the body below

    body: list[str] = []
    inner = _INDENT * (depth + 1)
    if isinstance(element, Package):
        # The visibility keyword is spec-legal and what parsers accept; a bare
        # `import` is rejected by the sysmlpy grammar.
        body.extend(f"{inner}public import {imp};" for imp in element.imports)
    body.extend(_doc_block(element, inner))
    if isinstance(element, RequirementUsage):
        if element.text:
            body.append(f"{inner}doc /* {element.text} */")
        if element.subject:
            body.append(f"{inner}subject {_name_of(model, element.subject)};")
    if isinstance(element, AnalysisCaseUsage):
        if element.subject:
            body.append(f"{inner}subject {_name_of(model, element.subject)};")
        if element.objective:
            body.append(f"{inner}objective {{ doc /* {element.objective} */ }}")
    if isinstance(element, ConstraintUsage) and element.expression:
        body.append(f"{inner}{{ {element.expression} }}")

    body.extend(_render(model, child, depth + 1, dep_names) for child in model.owned_by(element))

    if not body:
        return header + ";"
    return header + " {\n" + "\n".join(body) + f"\n{indent}}}"


def _render_connection(model: Model, element: ConnectionUsage, indent: str) -> str:
    scope = model.owner.get(element.element_id)
    label = f" {escape_name(element.declared_name)}" if element.declared_name else ""
    if element.source is None or element.target is None:
        return f"{indent}connection{label};"
    src = _relative_path(model, scope, element.source)
    tgt = _relative_path(model, scope, element.target)
    return f"{indent}connection{label} connect {src} to {tgt};"


def _render_attribute(model: Model, element: AttributeUsage, indent: str) -> str:
    header = indent + "attribute " + escape_name(element.declared_name or "unnamed")
    if element.definition:
        header += f" : {_name_of(model, element.definition)}"
    if element.value is not None:
        header += f" = {element.value.render()}"
    return header + ";"


def _render_metadata(model: Model, element: MetadataUsage, indent: str) -> str:
    about = f" about {_name_of(model, element.annotated)}" if element.annotated else ""
    name = f" {escape_name(element.declared_name)}" if element.declared_name else ""
    if not element.values:
        return f"{indent}metadata{name}{about};"
    inner = indent + _INDENT
    lines = [f"{inner}{escape_name(k)} = {_metadata_value(v)};" for k, v in element.values.items()]
    return f"{indent}metadata{name}{about} {{\n" + "\n".join(lines) + f"\n{indent}}}"


def _metadata_value(value: str | float | bool) -> str:
    """Render a metadata value in SysML syntax, not Python repr."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace('"', '\\"') + '"'
    return str(value)

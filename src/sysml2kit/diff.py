"""Element-level model diff.

Matching is by ``element_id`` by default; ``by_name=True`` falls back to
qualified names, for models whose parser regenerated the UUIDs. Semantic
(graph-aware) diffing is out of scope for v0.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sysml2kit.model.base import Element, Ref
from sysml2kit.model.container import Model

DiffKind = Literal["added", "removed", "changed", "moved"]


@dataclass(frozen=True)
class DiffEntry:
    """One difference between two models."""

    kind: DiffKind
    qualified_name: str
    detail: str = ""


def _key_map(model: Model, by_name: bool) -> dict[str | UUID, UUID]:
    if not by_name:
        return {eid: eid for eid in model.elements}
    return {model.qualified_name(eid): eid for eid in model.elements}


def _field_repr(element: Element, fieldname: str, model: Model) -> str:
    value = getattr(element, fieldname)
    if isinstance(value, Ref):
        try:
            return model.qualified_name(value.target)
        except KeyError:
            return f"<missing {value.target}>"
    return repr(value)


def diff_models(a: Model, b: Model, *, by_name: bool = False) -> list[DiffEntry]:
    """Compare two models; entries are sorted by qualified name within each kind."""
    keys_a = _key_map(a, by_name)
    keys_b = _key_map(b, by_name)

    added = [DiffEntry("added", b.qualified_name(keys_b[k])) for k in keys_b.keys() - keys_a]
    removed = [DiffEntry("removed", a.qualified_name(keys_a[k])) for k in keys_a.keys() - keys_b]

    changed: list[DiffEntry] = []
    moved: list[DiffEntry] = []
    for key in keys_a.keys() & keys_b.keys():
        ea, eb = a.elements[keys_a[key]], b.elements[keys_b[key]]
        name = a.qualified_name(ea)
        if type(ea) is not type(eb):
            changed.append(
                DiffEntry("changed", name, f"kind {type(ea).__name__} -> {type(eb).__name__}")
            )
            continue
        fields = [
            f
            for f in type(ea).model_fields
            if f != "element_id" and getattr(ea, f) != getattr(eb, f)
        ]
        # With name matching, refs differ whenever ids were regenerated; compare
        # them by the qualified name of what they point at instead.
        if by_name:
            fields = [
                f
                for f in fields
                if not (
                    isinstance(getattr(ea, f), Ref)
                    and _field_repr(ea, f, a) == _field_repr(eb, f, b)
                )
            ]
        if fields:
            details = ", ".join(
                f"{f}: {_field_repr(ea, f, a)} -> {_field_repr(eb, f, b)}" for f in fields
            )
            changed.append(DiffEntry("changed", name, details))
        owner_a = a.owner.get(ea.element_id)
        owner_b = b.owner.get(eb.element_id)
        owner_a_name = a.qualified_name(owner_a) if owner_a else None
        owner_b_name = b.qualified_name(owner_b) if owner_b else None
        if owner_a_name != owner_b_name:
            moved.append(DiffEntry("moved", name, f"{owner_a_name} -> {owner_b_name}"))

    out: list[DiffEntry] = []
    for group in (added, removed, changed, moved):
        out.extend(sorted(group, key=lambda e: e.qualified_name))
    return out


def render_diff(entries: list[DiffEntry]) -> str:
    """Render diff entries one per line, with +/-/~/> markers."""
    if not entries:
        return "(models are identical)"
    marker = {"added": "+", "removed": "-", "changed": "~", "moved": ">"}
    lines = []
    for e in entries:
        suffix = f"  ({e.detail})" if e.detail else ""
        lines.append(f"{marker[e.kind]} {e.qualified_name}{suffix}")
    return "\n".join(lines)

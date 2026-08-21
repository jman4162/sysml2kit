"""The Model container: element registry, identity, and ownership.

Ownership lives here (owner/owned maps keyed by element id), not on the
elements, mirroring how the Systems Modeling API keeps owning-relationship
records separate from element payloads.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Sequence
from uuid import UUID

from sysml2kit.model.base import Element, Ref, Relationship

#: Namespace for stable UUIDv5 ids derived from qualified names.
STABLE_ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "sysml2kit")


class Model:
    """A set of elements with identity, ownership, and lookup."""

    def __init__(self) -> None:
        self.elements: dict[UUID, Element] = {}
        self.owner: dict[UUID, UUID] = {}
        self.owned: dict[UUID, list[UUID]] = {}
        self.roots: list[UUID] = []

    # ------------------------------------------------------------- mutation
    def add(self, element: Element, owner: Element | UUID | None = None) -> Element:
        """Register an element, optionally under an owner already in the model."""
        eid = element.element_id
        if eid in self.elements:
            raise ValueError(f"duplicate element id {eid}")
        self.elements[eid] = element
        if owner is None:
            self.roots.append(eid)
        else:
            oid = owner if isinstance(owner, UUID) else owner.element_id
            if oid not in self.elements:
                raise KeyError(f"owner {oid} is not in the model")
            self.owner[eid] = oid
            self.owned.setdefault(oid, []).append(eid)
        return element

    def remove(self, element: Element | UUID) -> None:
        """Remove an element and reparent nothing: its owned elements become roots."""
        eid = element if isinstance(element, UUID) else element.element_id
        if eid not in self.elements:
            raise KeyError(f"element {eid} is not in the model")
        for child in self.owned.pop(eid, []):
            del self.owner[child]
            self.roots.append(child)
        oid = self.owner.pop(eid, None)
        if oid is None:
            self.roots.remove(eid)
        else:
            self.owned[oid].remove(eid)
        del self.elements[eid]

    # --------------------------------------------------------------- lookup
    def resolve(self, ref: Ref | UUID) -> Element:
        """Return the element a ref (or id) points at."""
        eid = ref.target if isinstance(ref, Ref) else ref
        return self.elements[eid]

    def owner_of(self, element: Element | UUID) -> Element | None:
        """Return the owning element, or None for a root."""
        eid = element if isinstance(element, UUID) else element.element_id
        oid = self.owner.get(eid)
        return self.elements[oid] if oid is not None else None

    def owned_by(self, element: Element | UUID) -> list[Element]:
        """Return the owned elements, in insertion order."""
        eid = element if isinstance(element, UUID) else element.element_id
        return [self.elements[cid] for cid in self.owned.get(eid, [])]

    def qualified_name(self, element: Element | UUID) -> str:
        """Return the ``::``-joined name path from the root to this element.

        Unnamed elements contribute their kind and a positional index, so the
        path is always defined (and usable for stable-id hashing).
        """
        eid = element if isinstance(element, UUID) else element.element_id
        parts: list[str] = []
        current: UUID | None = eid
        while current is not None:
            el = self.elements[current]
            parts.append(el.declared_name or self._positional_name(current))
            current = self.owner.get(current)
        return "::".join(reversed(parts))

    def _positional_name(self, eid: UUID) -> str:
        el = self.elements[eid]
        oid = self.owner.get(eid)
        siblings = self.owned.get(oid, []) if oid is not None else self.roots
        index = siblings.index(eid)
        return f"{type(el).__name__}#{index}"

    def find(
        self,
        *,
        name: str | None = None,
        kind: type[Element] | None = None,
    ) -> list[Element]:
        """Return elements matching a declared name and/or a class."""
        out: list[Element] = []
        for el in self.iter_elements(kind=kind):
            if name is not None and el.declared_name != name:
                continue
            out.append(el)
        return out

    def find_by_qualified_name(self, qualified: str) -> Element | None:
        """Return the element with this exact qualified name, if any."""
        for eid in self.elements:
            if self.qualified_name(eid) == qualified:
                return self.elements[eid]
        return None

    def iter_elements(self, *, kind: type[Element] | None = None) -> Iterator[Element]:
        """Iterate elements in ownership (depth-first) order."""
        for eid in self._walk():
            el = self.elements[eid]
            if kind is None or isinstance(el, kind):
                yield el

    def _walk(self) -> Iterator[UUID]:
        stack = list(reversed(self.roots))
        while stack:
            eid = stack.pop()
            yield eid
            stack.extend(reversed(self.owned.get(eid, [])))

    def relationships(
        self,
        *,
        kind: type[Relationship] | None = None,
        source: Element | UUID | None = None,
        target: Element | UUID | None = None,
    ) -> list[Relationship]:
        """Return relationships filtered by class and/or endpoint."""
        sid = source.element_id if isinstance(source, Element) else source
        tid = target.element_id if isinstance(target, Element) else target
        out: list[Relationship] = []
        for el in self.elements.values():
            if not isinstance(el, Relationship):
                continue
            if kind is not None and not isinstance(el, kind):
                continue
            if sid is not None and el.source.target != sid:
                continue
            if tid is not None and el.target.target != tid:
                continue
            out.append(el)
        return out

    # ------------------------------------------------------------ integrity
    def check_refs(self) -> list[tuple[UUID, str, UUID]]:
        """Return (element_id, field_name, missing_target) for dangling refs."""
        dangling: list[tuple[UUID, str, UUID]] = []
        for el in self.elements.values():
            for field, ref in self._refs_of(el):
                if ref.target not in self.elements:
                    dangling.append((el.element_id, field, ref.target))
        return dangling

    @staticmethod
    def _refs_of(element: Element) -> list[tuple[str, Ref]]:
        refs: list[tuple[str, Ref]] = []
        for field in type(element).model_fields:
            value = getattr(element, field)
            if isinstance(value, Ref):
                refs.append((field, value))
            elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
                refs.extend((field, item) for item in value if isinstance(item, Ref))
        return refs

    def assign_stable_ids(self) -> dict[UUID, UUID]:
        """Rewrite every element id as a UUIDv5 hash of its qualified name.

        Returns the old-to-new id mapping. Refs, ownership maps, and roots are
        remapped in place. Run this before committing generated interchange
        files so regeneration produces stable diffs.
        """
        mapping = {
            eid: uuid.uuid5(STABLE_ID_NAMESPACE, self.qualified_name(eid)) for eid in self.elements
        }
        if len(set(mapping.values())) != len(mapping):
            raise ValueError(
                "duplicate qualified names; stable ids need unique name paths "
                "(rename the clashing siblings, see validation rule S2K003)"
            )
        new_elements: dict[UUID, Element] = {}
        for eid, el in self.elements.items():
            updates: dict[str, object] = {"element_id": mapping[eid]}
            for field, ref in self._refs_of(el):
                value = getattr(el, field)
                if isinstance(value, Ref):
                    updates[field] = Ref(target=mapping.get(ref.target, ref.target))
            for field in type(el).model_fields:
                value = getattr(el, field)
                if (
                    isinstance(value, Sequence)
                    and not isinstance(value, str | bytes)
                    and any(isinstance(item, Ref) for item in value)
                ):
                    updates[field] = [
                        Ref(target=mapping.get(item.target, item.target))
                        if isinstance(item, Ref)
                        else item
                        for item in value
                    ]
            new_el = el.model_copy(update=updates)
            new_elements[new_el.element_id] = new_el
        self.elements = new_elements
        self.owner = {mapping[k]: mapping[v] for k, v in self.owner.items()}
        self.owned = {mapping[k]: [mapping[c] for c in v] for k, v in self.owned.items()}
        self.roots = [mapping[r] for r in self.roots]
        return mapping

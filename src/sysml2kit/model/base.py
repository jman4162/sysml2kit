"""Base element classes and the cross-reference type.

Every cross-reference between elements is a :class:`Ref` (a UUID wrapper),
never a direct Python object reference, so any element serializes on its own
and maps 1:1 onto the Systems Modeling API JSON ``{"@id": ...}`` form.
Ownership is not stored on elements either; the ``Model`` container keeps it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from sysml2kit.model.container import Model


class Ref(BaseModel):
    """Reference to another element by id."""

    model_config = ConfigDict(frozen=True)

    target: UUID

    @classmethod
    def to(cls, element: Element | UUID | Ref) -> Ref:
        """Build a Ref from an element, a UUID, or another Ref."""
        if isinstance(element, Ref):
            return element
        if isinstance(element, UUID):
            return cls(target=element)
        return cls(target=element.element_id)

    def resolve(self, model: Model) -> Element:
        """Return the referenced element, raising KeyError if absent."""
        return model.elements[self.target]


class Element(BaseModel):
    """Common base for every model element in the pragmatic profile."""

    model_config = ConfigDict(validate_assignment=True)

    element_id: UUID = Field(default_factory=uuid4)
    declared_name: str | None = None
    declared_short_name: str | None = None
    doc: str | None = None

    @property
    def label(self) -> str:
        """A human-readable identifier: name, short name, or the id."""
        return self.declared_name or self.declared_short_name or str(self.element_id)


class Relationship(Element):
    """Common base for reified relationships with a source and a target."""

    source: Ref
    target: Ref


class OpaqueElement(Element):
    """An element outside the pragmatic profile, preserved verbatim.

    ``raw`` holds the original JSON interchange record; it re-exports
    unchanged, so reading and writing a model does not drop content the
    profile has no class for.
    """

    type_name: str
    raw: dict[str, Any] = Field(default_factory=dict)

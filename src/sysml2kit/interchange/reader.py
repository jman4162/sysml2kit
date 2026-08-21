"""Read Systems Modeling API JSON records into a Model.

Unknown ``@type`` records become :class:`OpaqueElement` with the raw record
preserved verbatim (and ownership links kept), so re-export reproduces them
unchanged.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from sysml2kit.model.base import Element, OpaqueElement, Ref
from sysml2kit.model.container import Model
from sysml2kit.model.values import AttributeValue

from .typemap import TYPE_TO_CLASS

logger = logging.getLogger(__name__)


class InterchangeError(ValueError):
    """A record could not be turned into an element."""


def _snake(name: str) -> str:
    out = []
    for ch in name:
        if ch.isupper():
            out.append("_")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)


def _decode(field_type: Any, value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"@id"}:
        return Ref(target=UUID(value["@id"]))
    if isinstance(value, dict) and field_type is AttributeValue:
        return AttributeValue(**value)
    if (
        isinstance(value, list)
        and len(value) == 1
        and isinstance(value[0], dict)
        and set(value[0]) == {"@id"}
    ):
        # Servers speaking the full abstract syntax send relationship
        # endpoints as single-element lists; the profile keeps a single Ref.
        return Ref(target=UUID(value[0]["@id"]))
    if isinstance(value, list):
        return [_decode(None, item) for item in value]
    return value


def record_to_element(record: dict[str, Any]) -> Element:
    """Deserialize one interchange record to an element."""
    type_name = record.get("@type")
    if not isinstance(type_name, str):
        raise InterchangeError(f"record without a string @type: {record.get('@id', '?')}")
    eid = record.get("@id")
    if not isinstance(eid, str):
        raise InterchangeError(f"record without a string @id (type {type_name})")
    cls = TYPE_TO_CLASS.get(type_name)
    if cls is None:
        return OpaqueElement(element_id=UUID(eid), type_name=type_name, raw=dict(record))
    kwargs: dict[str, Any] = {"element_id": UUID(eid)}
    fields = cls.model_fields
    for key, value in record.items():
        if key in {"@id", "@type", "owningRelatedElement"}:
            continue
        field = _snake(key)
        if field not in fields:
            continue
        if value is None or value == []:
            # Servers echo empty lists / nulls for absent references.
            continue
        annotation = fields[field].annotation
        if (
            annotation in (str, str | None)
            and isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], str)
        ):
            # Full-abstract-syntax servers send e.g. requirement text as
            # List<String>; the profile keeps a single string.
            value = value[0]
        target_type = (
            AttributeValue if annotation in (AttributeValue, AttributeValue | None) else None
        )
        kwargs[field] = _decode(target_type, value)
    try:
        return cls(**kwargs)
    except ValidationError:
        # A known @type whose record doesn't fit the profile shape (e.g. a
        # server strips relationship endpoints): keep it opaquely rather than
        # fail the whole read, matching the passthrough guarantee.
        logger.warning("%s record %s does not fit the profile shape; kept opaque", type_name, eid)
        return OpaqueElement(element_id=UUID(eid), type_name=type_name, raw=dict(record))


def _membership_ref(record: dict[str, Any], *keys: str) -> UUID | None:
    """First resolvable ``{"@id"}`` (scalar or single-element list) among keys."""
    for key in keys:
        value = record.get(key)
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        if isinstance(value, dict) and isinstance(value.get("@id"), str):
            return UUID(value["@id"])
    return None


def model_from_json(data: list[dict[str, Any]] | str | Path) -> Model:
    """Build a Model from a record list, a JSON string, or a file path."""
    if isinstance(data, Path):
        records = json.loads(data.read_text())
    elif isinstance(data, str):
        # JSON text starts with a bracket after whitespace; anything else is a path.
        text = data if data.lstrip().startswith("[") else Path(data).read_text()
        records = json.loads(text)
    else:
        records = data
    if not isinstance(records, list):
        raise InterchangeError("interchange JSON must be a list of records")

    model = Model()
    owners: dict[UUID, UUID] = {}
    for record in records:
        if record.get("@type") == "OwningMembership":
            # Servers speaking the full abstract syntax carry ownership as
            # OwningMembership records; fold them into the owner map instead
            # of keeping them as elements.
            member = _membership_ref(record, "memberElement", "ownedMemberElement")
            owner = _membership_ref(record, "membershipOwningNamespace", "owningRelatedElement")
            if member is not None and owner is not None:
                owners[member] = owner
            else:
                logger.warning(
                    "OwningMembership %s without resolvable ends; dropped", record.get("@id")
                )
            continue
        element = record_to_element(record)
        model.elements[element.element_id] = element
        owning = record.get("owningRelatedElement")
        if isinstance(owning, dict) and "@id" in owning:
            owners[element.element_id] = UUID(owning["@id"])

    for eid, oid in owners.items():
        if oid in model.elements:
            model.owner[eid] = oid
            model.owned.setdefault(oid, []).append(eid)
    model.roots = [eid for eid in model.elements if eid not in model.owner]
    return model

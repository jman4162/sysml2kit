"""Read Systems Modeling API JSON records into a Model.

Unknown ``@type`` records become :class:`OpaqueElement` with the raw record
preserved verbatim (and ownership links kept), so re-export reproduces them
unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from sysml2kit.model.base import Element, OpaqueElement, Ref
from sysml2kit.model.container import Model
from sysml2kit.model.values import AttributeValue

from .typemap import TYPE_TO_CLASS


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
        annotation = fields[field].annotation
        target_type = (
            AttributeValue if annotation in (AttributeValue, AttributeValue | None) else None
        )
        kwargs[field] = _decode(target_type, value)
    try:
        return cls(**kwargs)
    except ValidationError as exc:
        raise InterchangeError(f"invalid {type_name} record {eid}: {exc}") from exc


def model_from_json(data: list[dict[str, Any]] | str | Path) -> Model:
    """Build a Model from a record list, a JSON string, or a file path."""
    if isinstance(data, Path):
        records = json.loads(data.read_text())
    elif isinstance(data, str):
        source = Path(data)
        text = source.read_text() if source.exists() else data
        records = json.loads(text)
    else:
        records = data
    if not isinstance(records, list):
        raise InterchangeError("interchange JSON must be a list of records")

    model = Model()
    owners: dict[UUID, UUID] = {}
    for record in records:
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

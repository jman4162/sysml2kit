"""Write a Model as Systems Modeling API JSON records.

Output is deterministic — elements sorted by qualified name, keys sorted
within each record — so committed interchange files diff cleanly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sysml2kit.model.base import Element, OpaqueElement, Ref
from sysml2kit.model.container import Model
from sysml2kit.model.values import AttributeValue

from .typemap import CLASS_TO_TYPE

#: Element fields serialized by the generic path for every class.
_COMMON_FIELDS = ("declared_name", "declared_short_name", "doc")


def _camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(word.capitalize() for word in tail)


def _encode(value: Any) -> Any:
    if isinstance(value, Ref):
        return {"@id": str(value.target)}
    if isinstance(value, UUID):
        return {"@id": str(value)}
    if isinstance(value, AttributeValue):
        return {k: v for k, v in value.model_dump().items() if v is not None}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    return value


def element_to_record(model: Model, element: Element) -> dict[str, Any]:
    """Serialize one element to its interchange record."""
    if isinstance(element, OpaqueElement):
        return dict(element.raw)
    type_name = CLASS_TO_TYPE.get(type(element))
    if type_name is None:
        raise TypeError(f"no @type mapping for {type(element).__name__}")
    record: dict[str, Any] = {"@id": str(element.element_id), "@type": type_name}
    owner = model.owner.get(element.element_id)
    if owner is not None:
        record["owningRelatedElement"] = {"@id": str(owner)}
    for field in type(element).model_fields:
        if field == "element_id":
            continue
        value = getattr(element, field)
        if value is None or value == [] or value == {}:
            continue
        record[_camel(field)] = _encode(value)
    return record


def model_to_json(model: Model) -> list[dict[str, Any]]:
    """Serialize the model to a sorted list of interchange records."""
    ordered = sorted(model.elements.values(), key=lambda el: model.qualified_name(el))
    return [
        {k: record[k] for k in sorted(record)}
        for record in (element_to_record(model, el) for el in ordered)
    ]


def write_json(model: Model, path: str | Path) -> None:
    """Write the model to a JSON file with a trailing newline."""
    Path(path).write_text(json.dumps(model_to_json(model), indent=2) + "\n")

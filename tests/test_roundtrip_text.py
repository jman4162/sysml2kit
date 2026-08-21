"""Write a model to textual notation, parse it back with sysmlpy, compare.

The comparison is structural (names, kinds, ownership paths) because sysmlpy
0.36 regenerates ids and does not surface typing/values on its wrappers.
"""

import pytest

pytest.importorskip("sysmlpy")

from sysml2kit.backends import get_backend
from sysml2kit.model import (
    Model,
    Package,
    PartDefinition,
    PartUsage,
    PortUsage,
    RequirementUsage,
)
from sysml2kit.text import write_model

pytestmark = pytest.mark.parse

COMPARED_KINDS = (Package, PartDefinition, PartUsage, PortUsage, RequirementUsage)


def structural_signature(model: Model) -> set[tuple[str, str]]:
    return {
        (type(el).__name__, model.qualified_name(el))
        for kind in COMPARED_KINDS
        for el in model.iter_elements(kind=kind)
        if type(el) in COMPARED_KINDS
    }


def test_vehicle_text_round_trip(vehicle: Model):
    text = write_model(vehicle)
    reparsed = get_backend("sysmlpy").parse(text)
    assert structural_signature(reparsed) == structural_signature(vehicle)


def test_written_text_is_accepted_at_all(vehicle: Model):
    # A parse that raises would mean the writer emits illegal notation.
    get_backend("sysmlpy").parse(write_model(vehicle), filename="vehicle.sysml")

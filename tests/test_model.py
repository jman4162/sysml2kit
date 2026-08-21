from uuid import uuid4

import pytest

from sysml2kit.model import (
    Model,
    Package,
    PartUsage,
    RequirementUsage,
    SatisfyRelationship,
)


def test_add_and_resolve(vehicle: Model):
    battery = vehicle.find(name="battery")[0]
    assert vehicle.resolve(battery.element_id) is battery


def test_duplicate_id_rejected(vehicle: Model):
    battery = vehicle.find(name="battery")[0]
    with pytest.raises(ValueError, match="duplicate"):
        vehicle.add(battery)


def test_owner_requires_membership():
    model = Model()
    stranger = Package(declared_name="Elsewhere")
    with pytest.raises(KeyError):
        model.add(Package(declared_name="P"), owner=stranger)


def test_qualified_name(vehicle: Model):
    battery = vehicle.find(name="battery")[0]
    assert vehicle.qualified_name(battery) == "Vehicle::battery"


def test_qualified_name_unnamed_elements(vehicle: Model):
    rels = vehicle.relationships(kind=SatisfyRelationship)
    assert len(rels) == 1
    name = vehicle.qualified_name(rels[0])
    assert "SatisfyRelationship#" in name


def test_find_by_kind(vehicle: Model):
    parts = vehicle.find(kind=PartUsage)
    assert {p.declared_name for p in parts} == {"battery", "motor"}


def test_find_by_qualified_name(vehicle: Model):
    el = vehicle.find_by_qualified_name("Vehicle::battery")
    assert el is not None
    assert isinstance(el, PartUsage)


def test_iter_is_depth_first(vehicle: Model):
    names = [el.declared_name for el in vehicle.iter_elements()]
    assert names.index("Vehicle") == 0
    assert names.index("capacity") > names.index("battery")


def test_relationship_filters(vehicle: Model):
    battery = vehicle.find(name="battery")[0]
    req = next(
        el
        for el in vehicle.iter_elements(kind=RequirementUsage)
        if el.declared_short_name == "REQ-002"
    )
    rels = vehicle.relationships(kind=SatisfyRelationship, source=battery, target=req)
    assert len(rels) == 1


def test_check_refs_reports_dangling(vehicle: Model):
    assert vehicle.check_refs() == []
    battery = vehicle.find(name="battery")[0]
    from sysml2kit.model import Ref

    rel = SatisfyRelationship(source=Ref.to(battery), target=Ref(target=uuid4()))
    vehicle.add(rel)
    dangling = vehicle.check_refs()
    assert len(dangling) == 1
    assert dangling[0][1] == "target"


def test_remove_reparents_children_to_roots(vehicle: Model):
    battery = vehicle.find(name="battery")[0]
    children = vehicle.owned_by(battery)
    vehicle.remove(battery)
    assert battery.element_id not in vehicle.elements
    for child in children:
        assert child.element_id in vehicle.roots


def test_assign_stable_ids_is_deterministic(vehicle: Model):
    first = vehicle.assign_stable_ids()
    battery = vehicle.find(name="battery")[0]
    id_after_first = battery.element_id
    second = vehicle.assign_stable_ids()
    assert vehicle.find(name="battery")[0].element_id == id_after_first
    assert set(second.keys()) == set(second.values())  # second pass is identity
    assert first  # first pass produced a mapping


def test_assign_stable_ids_remaps_refs(vehicle: Model):
    vehicle.assign_stable_ids()
    assert vehicle.check_refs() == []

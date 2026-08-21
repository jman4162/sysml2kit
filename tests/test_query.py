from sysml2kit.model import Model, RequirementUsage
from sysml2kit.query import (
    allocation_table,
    derived_from,
    parts_of,
    requirements_in,
    satisfied_by,
    trace_matrix,
    unsatisfied_requirements,
    unverified_requirements,
    verified_by,
)


def req_by_short(model: Model, short: str) -> RequirementUsage:
    return next(r for r in requirements_in(model) if r.declared_short_name == short)


def test_requirements_in(vehicle: Model):
    assert {r.declared_short_name for r in requirements_in(vehicle)} == {"REQ-001", "REQ-002"}


def test_parts_of_scoped(vehicle: Model):
    pkg = vehicle.find(name="Vehicle")[0]
    assert {p.declared_name for p in parts_of(vehicle, pkg)} == {"battery", "motor"}


def test_satisfied_and_verified(vehicle: Model):
    mass = req_by_short(vehicle, "REQ-002")
    range_ = req_by_short(vehicle, "REQ-001")
    assert [el.declared_name for el in satisfied_by(vehicle, mass)] == ["battery"]
    assert [el.declared_name for el in verified_by(vehicle, range_)] == ["RangeAnalysis"]


def test_derived_from(vehicle: Model):
    mass = req_by_short(vehicle, "REQ-002")
    assert [r.declared_short_name for r in derived_from(vehicle, mass)] == ["REQ-001"]


def test_unsatisfied_and_unverified(vehicle: Model):
    assert {r.declared_short_name for r in unsatisfied_requirements(vehicle)} == {"REQ-001"}
    assert {r.declared_short_name for r in unverified_requirements(vehicle)} == {"REQ-002"}


def test_allocation_table(vehicle: Model):
    table = allocation_table(vehicle)
    assert len(table) == 1
    assert table[0][0].declared_short_name == "REQ-001"
    assert table[0][1].declared_name == "battery"


def test_trace_matrix(vehicle: Model):
    matrix = trace_matrix(vehicle)
    rendered = matrix.render()
    assert "REQ-001" in rendered
    assert "battery" in rendered
    mass = req_by_short(vehicle, "REQ-002")
    battery = vehicle.find(name="battery")[0]
    assert matrix.cells[(str(mass.element_id), str(battery.element_id))] == {"satisfy"}

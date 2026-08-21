from sysml2kit.diff import diff_models, render_diff
from sysml2kit.interchange import model_from_json, model_to_json
from sysml2kit.model import Model, builder


def clone(model: Model) -> Model:
    return model_from_json(model_to_json(model))


def test_identical_models(vehicle: Model):
    assert diff_models(vehicle, clone(vehicle)) == []
    assert render_diff([]) == "(models are identical)"


def test_added_and_removed(vehicle: Model):
    other = clone(vehicle)
    pkg = other.find(name="Vehicle")[0]
    builder.part(other, "charger", owner=pkg)
    entries = diff_models(vehicle, other)
    assert [e.kind for e in entries] == ["added"]
    assert entries[0].qualified_name == "Vehicle::charger"
    reverse = diff_models(other, vehicle)
    assert [e.kind for e in reverse] == ["removed"]


def test_changed_field(vehicle: Model):
    other = clone(vehicle)
    motor = other.find(name="motor")[0]
    motor.multiplicity = "[4]"  # type: ignore[attr-defined]
    entries = diff_models(vehicle, other)
    assert len(entries) == 1
    assert entries[0].kind == "changed"
    assert "multiplicity" in entries[0].detail


def test_moved(vehicle: Model):
    other = clone(vehicle)
    motor = other.find(name="motor")[0]
    battery = other.find(name="battery")[0]
    pkg_id = other.owner[motor.element_id]
    other.owned[pkg_id].remove(motor.element_id)
    other.owner[motor.element_id] = battery.element_id
    other.owned.setdefault(battery.element_id, []).append(motor.element_id)
    entries = diff_models(vehicle, other)
    assert any(e.kind == "moved" and "battery" in e.detail for e in entries)


def test_by_name_matching_survives_new_ids(vehicle: Model):
    other = clone(vehicle)
    other.assign_stable_ids()  # every id changes
    assert diff_models(vehicle, other, by_name=True) == []
    by_id = diff_models(vehicle, other, by_name=False)
    assert by_id  # id-keyed matching sees total replacement


def test_render_markers(vehicle: Model):
    other = clone(vehicle)
    pkg = other.find(name="Vehicle")[0]
    builder.part(other, "charger", owner=pkg)
    out = render_diff(diff_models(vehicle, other))
    assert out.startswith("+ Vehicle::charger")

import json

from sysml2kit.interchange import model_from_json, model_to_json
from sysml2kit.model import Model, OpaqueElement, PartUsage


def test_fixpoint_on_vehicle(vehicle: Model):
    first = model_to_json(vehicle)
    second = model_to_json(model_from_json(first))
    assert first == second


def test_ownership_round_trips(vehicle: Model):
    restored = model_from_json(model_to_json(vehicle))
    battery = restored.find(name="battery")[0]
    assert restored.qualified_name(battery) == "Vehicle::battery"


def test_values_round_trip(vehicle: Model):
    restored = model_from_json(model_to_json(vehicle))
    capacity = restored.find(name="capacity")[0]
    assert capacity.value.value == 75.0  # type: ignore[union-attr]
    assert capacity.value.unit == "kWh"  # type: ignore[union-attr]
    assert capacity.value.source == "vendor datasheet"  # type: ignore[union-attr]


def test_unknown_type_becomes_opaque_and_survives(vehicle: Model):
    records = model_to_json(vehicle)
    pkg_id = records[0]["@id"]
    alien = {
        "@id": "00000000-0000-4000-8000-000000000abc",
        "@type": "StateUsage",
        "declaredName": "charging",
        "owningRelatedElement": {"@id": pkg_id},
        "customField": {"nested": [1, 2, 3]},
    }
    restored = model_from_json([*records, alien])
    opaque = [el for el in restored.iter_elements() if isinstance(el, OpaqueElement)]
    assert len(opaque) == 1
    assert opaque[0].type_name == "StateUsage"
    again = model_to_json(restored)
    alien_out = next(r for r in again if r.get("@type") == "StateUsage")
    assert alien_out == {k: alien[k] for k in sorted(alien)}


def test_json_string_and_list_inputs_agree(vehicle: Model):
    records = model_to_json(vehicle)
    from_string = model_from_json(json.dumps(records))
    assert model_to_json(from_string) == records


def test_multiplicity_round_trips(vehicle: Model):
    restored = model_from_json(model_to_json(vehicle))
    motor = restored.find(name="motor")[0]
    assert isinstance(motor, PartUsage)
    assert motor.multiplicity == "[2]"

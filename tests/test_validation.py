from uuid import uuid4

from sysml2kit.model import (
    Model,
    PartUsage,
    Ref,
    SatisfyRelationship,
    builder,
)
from sysml2kit.validation import RULES, validate


def ids(issues):
    return {i.rule_id for i in issues}


def test_vehicle_has_no_errors(vehicle: Model):
    assert not [i for i in validate(vehicle) if i.severity == "error"]


def test_s2k001_dangling_ref(vehicle: Model):
    battery = vehicle.find(name="battery")[0]
    vehicle.add(SatisfyRelationship(source=Ref.to(battery), target=Ref(target=uuid4())))
    assert "S2K001" in ids(validate(vehicle))


def test_s2k002_duplicate_requirement_id(vehicle: Model):
    pkg = vehicle.find(name="Vehicle")[0]
    builder.req(vehicle, "REQ-001", "RangeCopy", owner=pkg)
    assert "S2K002" in ids(validate(vehicle))


def test_s2k003_sibling_clash(vehicle: Model):
    pkg = vehicle.find(name="Vehicle")[0]
    builder.part(vehicle, "battery", owner=pkg)
    assert "S2K003" in ids(validate(vehicle))


def test_s2k004_wrong_endpoint_kind(vehicle: Model):
    battery = vehicle.find(name="battery")[0]
    motor = vehicle.find(name="motor")[0]
    builder.satisfy(vehicle, source=battery, target=motor)  # target is not a requirement
    assert "S2K004" in ids(validate(vehicle))


def test_s2k005_missing_definition(vehicle: Model):
    pkg = vehicle.find(name="Vehicle")[0]
    vehicle.add(PartUsage(declared_name="orphan", definition=Ref(target=uuid4())), owner=pkg)
    issues = ids(validate(vehicle))
    assert "S2K005" in issues


def test_s2k006_bad_unit(vehicle: Model):
    battery = vehicle.find(name="battery")[0]
    builder.attr(vehicle, "weird", 1.0, owner=battery, unit="blorps")
    assert "S2K006" in ids(validate(vehicle))


def test_s2k007_requirement_without_subject_or_satisfier(vehicle: Model):
    pkg = vehicle.find(name="Vehicle")[0]
    builder.req(vehicle, "REQ-999", "Floating", owner=pkg)
    issues = validate(vehicle)
    flagged = [i for i in issues if i.rule_id == "S2K007"]
    assert any("Floating" in i.message for i in flagged)


def test_s2k008_empty_package():
    model = Model()
    builder.pkg(model, "Empty")
    assert "S2K008" in ids(validate(model))


def test_errors_sort_first(vehicle: Model):
    pkg = vehicle.find(name="Vehicle")[0]
    builder.req(vehicle, "REQ-001", "RangeCopy2", owner=pkg)  # S2K002 error
    issues = validate(vehicle)
    severities = [i.severity for i in issues]
    assert severities == sorted(severities, key={"error": 0, "warning": 1, "info": 2}.__getitem__)


def test_rule_registry_is_complete():
    assert set(RULES) == {f"S2K00{n}" for n in range(1, 10)} | {"S2K010"}


def test_s2k010_duplicate_fidelity_labels(vehicle: Model):
    analysis = vehicle.find(name="RangeAnalysis")[0]
    builder.metadata(
        vehicle, analysis, {"engine": "a", "fidelity": "x"}, name="verificationBinding"
    )
    builder.metadata(
        vehicle, analysis, {"engine": "b", "fidelity": "x"}, name="verificationBinding"
    )
    assert "S2K010" in ids(validate(vehicle))


def test_s2k010_mixed_labeling_warns(vehicle: Model):
    analysis = vehicle.find(name="RangeAnalysis")[0]
    builder.metadata(
        vehicle, analysis, {"engine": "a", "fidelity": "x"}, name="verificationBinding"
    )
    builder.metadata(vehicle, analysis, {"engine": "b"}, name="verificationBinding")
    issues = [i for i in validate(vehicle) if i.rule_id == "S2K010"]
    assert issues
    assert issues[0].severity == "warning"

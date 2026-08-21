from sysml2kit.model import Model, builder
from sysml2kit.text import write_model, write_package


def test_vehicle_golden(vehicle: Model, file_regression):
    file_regression.check(write_model(vehicle), extension=".sysml")


def test_output_is_deterministic(vehicle: Model):
    assert write_model(vehicle) == write_model(vehicle)


def test_empty_definitions_get_semicolons():
    model = Model()
    pkg = builder.pkg(model, "P")
    builder.part_def(model, "Widget", owner=pkg)
    out = write_model(model)
    assert "part def Widget;" in out


def test_name_quoting():
    model = Model()
    builder.pkg(model, "Has Spaces")
    assert "package 'Has Spaces'" in write_model(model)


def test_requirement_block(vehicle: Model):
    out = write_model(vehicle)
    assert "requirement <'REQ-001'> Range {" in out
    assert "doc /* The vehicle shall travel at least 400 km on one charge. */" in out


def test_attribute_value_rendering(vehicle: Model):
    assert "attribute capacity = 75.0 [kWh];" in write_model(vehicle)


def test_relations_render(vehicle: Model):
    out = write_model(vehicle)
    assert "satisfy BatteryMass by battery;" in out
    assert "dependency from RangeAnalysis to Range; // verify" in out
    assert "dependency from BatteryMass to Range; // derive" in out
    assert "allocate Range to battery;" in out


def test_connection_uses_relative_paths(vehicle: Model):
    assert "connection powerFeed connect battery.dcBus to motor.dcIn;" in write_model(vehicle)


def test_write_package_scopes_output(vehicle: Model):
    pkg = vehicle.find(name="Vehicle")[0]
    assert write_package(vehicle, pkg) == write_model(vehicle)

import pytest

from sysml2kit.model import Model, builder


@pytest.fixture
def vehicle() -> Model:
    """A small domain-neutral model exercising every relationship kind."""
    model = Model()
    pkg = builder.pkg(model, "Vehicle", doc="Demonstration vehicle model.")
    battery_def = builder.part_def(model, "Battery", owner=pkg)
    battery = builder.part(model, "battery", owner=pkg, definition=battery_def)
    motor = builder.part(model, "motor", owner=pkg, multiplicity="[2]")
    builder.attr(model, "capacity", 75.0, owner=battery, unit="kWh", source="vendor datasheet")
    dc_bus = builder.port(model, "dcBus", owner=battery)
    motor_in = builder.port(model, "dcIn", owner=motor)
    builder.connect(model, dc_bus, motor_in, owner=pkg, name="powerFeed")

    range_req = builder.req(
        model,
        "REQ-001",
        "Range",
        owner=pkg,
        text="The vehicle shall travel at least 400 km on one charge.",
    )
    mass_req = builder.req(
        model,
        "REQ-002",
        "BatteryMass",
        owner=pkg,
        text="The battery shall weigh at most 500 kg.",
        subject=battery,
    )
    builder.derive(model, source=mass_req, target=range_req)
    builder.satisfy(model, source=battery, target=mass_req)
    builder.allocate(model, source=range_req, target=battery)

    range_analysis = builder.analysis(
        model,
        "RangeAnalysis",
        owner=pkg,
        subject=battery,
        objective="Show the range requirement holds at nominal load.",
    )
    builder.verify(model, source=range_analysis, target=range_req)
    return model

from sysml2kit.interop import extract_requirements
from sysml2kit.model import Model, builder


def checkable_model() -> Model:
    model = Model()
    pkg = builder.pkg(model, "Terminal")
    array = builder.part(model, "array", owner=pkg)
    eirp = builder.req(
        model, "REQ-EIRP", "EirpFloor", owner=pkg, text="EIRP shall be at least 52 dBW."
    )
    builder.attr(model, "metricKey", "eirp_dbw", owner=eirp)
    builder.attr(model, "threshold", 52.0, owner=eirp, unit="dBW")
    builder.attr(model, "op", ">=", owner=eirp)
    builder.attr(model, "severity", "must", owner=eirp)
    builder.satisfy(model, source=array, target=eirp)

    sll = builder.req(model, "REQ-SLL", "SidelobeCeiling", owner=pkg)
    builder.attr(model, "metricKey", "sidelobe_db", owner=sll)
    builder.attr(model, "threshold", -20.0, owner=sll, unit="dB")
    builder.attr(model, "op", "<=", owner=sll)
    builder.attr(model, "severity", "should", owner=sll)

    builder.req(model, "REQ-PROSE", "ProseOnly", owner=pkg, text="No metric attached.")
    return model


def test_extracts_only_metric_requirements():
    specs = extract_requirements(checkable_model())
    assert [s.id for s in specs] == ["REQ-EIRP", "REQ-SLL"]


def test_dual_form_thresholds():
    eirp, sll = extract_requirements(checkable_model())
    assert (eirp.op, eirp.value, eirp.minimum, eirp.maximum) == (">=", 52.0, 52.0, None)
    assert (sll.op, sll.value, sll.minimum, sll.maximum) == ("<=", -20.0, None, -20.0)
    assert eirp.units == "dBW"
    assert sll.severity == "should"


def test_traceability_captured():
    eirp = extract_requirements(checkable_model())[0]
    assert eirp.satisfied_by == ["Terminal::array"]
    assert eirp.verified_by == []


def test_shapes_project_into_both_dialects():
    """Freeze the adapter contract without importing PAS or aedl."""
    for spec in extract_requirements(checkable_model()):
        # phased-array-systems op-form: Requirement(id, name, metric_key, op, value, units, severity)
        pas_shape = {
            "id": spec.id,
            "name": spec.name,
            "metric_key": spec.metric_key,
            "op": spec.op,
            "value": spec.value,
            "units": spec.units,
            "severity": spec.severity,
        }
        assert None not in (pas_shape["op"], pas_shape["value"])
        # aedl bound-form: Requirement(id, metric, max, min) with exactly one bound
        # (== maps to a two-sided bound, which aedl models as two requirements)
        aedl_shape = {
            "id": spec.id,
            "metric": spec.metric_key,
            "min": spec.minimum,
            "max": spec.maximum,
        }
        assert aedl_shape["min"] is not None or aedl_shape["max"] is not None


def test_equality_op_sets_both_bounds():
    model = Model()
    pkg = builder.pkg(model, "P")
    req = builder.req(model, "REQ-X", "Exact", owner=pkg)
    builder.attr(model, "metricKey", "x", owner=req)
    builder.attr(model, "threshold", 5.0, owner=req)
    builder.attr(model, "op", "==", owner=req)
    spec = extract_requirements(model)[0]
    assert (spec.minimum, spec.maximum) == (5.0, 5.0)


def test_requirement_spec_schema_is_frozen():
    """Downstream adapters (phased-array-systems, aedl) consume these fields.

    Changing this set is a compatibility decision, not a refactor: update the
    adapters in those repos in the same release.
    """
    from sysml2kit.interop import RequirementSpec

    assert set(RequirementSpec.model_fields) == {
        "id",
        "name",
        "metric_key",
        "op",
        "value",
        "minimum",
        "maximum",
        "units",
        "severity",
        "source_element_id",
        "satisfied_by",
        "verified_by",
    }

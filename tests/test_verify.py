import json
from importlib import metadata as importlib_metadata

import pytest

from sysml2kit.model import AttributeUsage, Model, builder
from sysml2kit.model.metadata import MetadataUsage
from sysml2kit.verify import (
    BindingError,
    EngineNotFoundError,
    EngineRegistry,
    apply_results,
    build_payload,
    extract_bindings,
    run_verification,
)


def bound_model(threshold=400.0, op=">=", engine="fake", config_ref=None, overrides=None):
    model = Model()
    pkg = builder.pkg(model, "Vehicle")
    battery = builder.part(model, "battery", owner=pkg)
    req = builder.req(model, "REQ-001", "Range", owner=pkg, subject=battery)
    builder.attr(model, "metricKey", "range_km", owner=req)
    builder.attr(model, "threshold", threshold, owner=req, unit="km")
    builder.attr(model, "op", op, owner=req)
    analysis = builder.analysis(model, "RangeAnalysis", owner=pkg, subject=battery)
    builder.verify(model, source=analysis, target=req, owner=pkg)
    values = {"engine": engine}
    if config_ref:
        values["configRef"] = config_ref
    values.update(overrides or {})
    builder.metadata(model, analysis, values, name="verificationBinding")
    return model


def registry_with(metrics):
    registry = EngineRegistry()
    registry.register("fake", lambda payload: metrics, dist=None)
    return registry


def test_extract_bindings():
    model = bound_model(config_ref="cfg.json", overrides={"payload.scenario.range_km": 500})
    (binding,) = extract_bindings(model)
    assert binding.engine == "fake"
    assert binding.analysis == "Vehicle::RangeAnalysis"
    assert binding.config_ref == "cfg.json"
    assert binding.overrides == {"scenario.range_km": 500}


def test_pass_verdict_with_margin():
    run = run_verification(bound_model(), registry=registry_with({"range_km": 420.0}))
    assert run.passed
    (verdict,) = run.requirements
    assert verdict.status == "pass"
    assert verdict.actual == 420.0
    assert verdict.margin == pytest.approx(20.0)
    assert verdict.units == "km"


def test_fail_verdict():
    run = run_verification(bound_model(), registry=registry_with({"range_km": 380.0}))
    assert not run.passed
    assert run.requirements[0].status == "fail"
    assert run.requirements[0].margin == pytest.approx(-20.0)


def test_missing_metric_is_unknown():
    run = run_verification(bound_model(), registry=registry_with({"other": 1.0}))
    (verdict,) = run.requirements
    assert verdict.status == "unknown"
    assert not run.passed  # a must-requirement stuck at unknown does not pass


def test_non_numeric_metric_is_unknown():
    run = run_verification(bound_model(), registry=registry_with({"range_km": "lots"}))
    assert run.requirements[0].status == "unknown"


def test_engine_exception_captured_not_raised():
    registry = EngineRegistry()

    def boom(payload):
        raise RuntimeError("solver diverged")

    registry.register("fake", boom)
    run = run_verification(bound_model(), registry=registry)
    assert run.analyses[0].error is not None
    assert "solver diverged" in run.analyses[0].error
    assert not run.passed


def test_missing_engine_lists_available():
    registry = EngineRegistry()
    registry.register("present", lambda p: {})
    run = run_verification(bound_model(engine="absent"), registry=registry)
    assert "present" in (run.analyses[0].error or "")


def test_config_ref_loaded_and_overridden(tmp_path):
    (tmp_path / "cfg.json").write_text(json.dumps({"scenario": {"range_km": 100, "keep": 1}}))
    model = bound_model(config_ref="cfg.json", overrides={"payload.scenario.range_km": 999})
    captured = {}

    def spy(payload):
        captured.update(payload)
        return {"range_km": 420.0}

    registry = EngineRegistry()
    registry.register("fake", spy)
    run_verification(model, registry=registry, model_path=tmp_path / "model.json")
    assert captured == {"scenario": {"range_km": 999, "keep": 1}}


def test_config_ref_escape_rejected(tmp_path):
    model = bound_model(config_ref="../outside.json")
    run = run_verification(model, registry=registry_with({}), model_path=tmp_path / "model.json")
    assert "escapes" in (run.analyses[0].error or "")


def test_yaml_config_needs_extra_or_works(tmp_path):
    pytest.importorskip("yaml")
    (tmp_path / "cfg.yaml").write_text("scenario:\n  range_km: 123\n")
    binding = extract_bindings(bound_model(config_ref="cfg.yaml"))[0]
    assert build_payload(binding, tmp_path) == {"scenario": {"range_km": 123}}


def test_analyses_filter():
    run = run_verification(
        bound_model(),
        registry=registry_with({"range_km": 420.0}),
        analyses=["Vehicle::SomethingElse"],
    )
    assert run.analyses == []
    assert run.requirements == []


def test_binding_on_non_analysis_rejected():
    model = Model()
    pkg = builder.pkg(model, "P")
    part = builder.part(model, "b", owner=pkg)
    builder.metadata(model, part, {"engine": "fake"}, name="verificationBinding")
    with pytest.raises(BindingError, match="analysis"):
        extract_bindings(model)


def test_registry_discovery_via_entry_points(monkeypatch):
    class FakeDist:
        name = "fake-dist"

    class FakeEntryPoint:
        name = "discovered"
        dist = FakeDist()

        def load(self):
            return lambda payload: {"m": 1.0}

    monkeypatch.setattr(importlib_metadata, "entry_points", lambda group: [FakeEntryPoint()])
    registry = EngineRegistry.discover()
    assert registry.names() == ["discovered"]
    assert registry.get("discovered")({}) == {"m": 1.0}
    with pytest.raises(EngineNotFoundError, match="discovered"):
        registry.get("nope")


def test_write_back_provenance_and_idempotency():
    model = bound_model()
    registry = registry_with({"range_km": 420.0})
    run = run_verification(model, registry=registry, timestamp="2026-08-21T12:00:00Z")
    added_first = apply_results(model, run)
    assert added_first == 2  # one attribute + one verdict metadata

    analysis = model.find(name="RangeAnalysis")[0]
    written = [
        el
        for el in model.owned_by(analysis)
        if isinstance(el, AttributeUsage) and el.declared_name == "range_km"
    ]
    assert len(written) == 1
    assert written[0].value.value == 420.0
    assert written[0].value.unit == "km"
    assert written[0].value.source.startswith("sysml2kit.verify")
    assert "2026-08-21T12:00:00Z" in written[0].value.source

    req = model.find(name="Range")[0]
    verdicts = [
        el
        for el in model.owned_by(req)
        if isinstance(el, MetadataUsage) and el.declared_name == "verificationVerdict"
    ]
    assert len(verdicts) == 1
    assert verdicts[0].values["status"] == "pass"

    # second application replaces, not duplicates
    apply_results(model, run)
    assert (
        len(
            [
                el
                for el in model.owned_by(analysis)
                if isinstance(el, AttributeUsage) and el.declared_name == "range_km"
            ]
        )
        == 1
    )
    assert (
        len(
            [
                el
                for el in model.owned_by(req)
                if isinstance(el, MetadataUsage) and el.declared_name == "verificationVerdict"
            ]
        )
        == 1
    )


def test_multiple_bindings_first_wins_consistently(caplog):
    """Hotfix regression: checking and write-back provenance must agree."""
    model = bound_model()
    analysis = model.find(name="RangeAnalysis")[0]
    builder.metadata(model, analysis, {"engine": "second"}, name="verificationBinding")
    registry = EngineRegistry()
    registry.register("fake", lambda p: {"range_km": 420.0})
    registry.register("second", lambda p: {"range_km": 1.0})  # would fail the check
    import logging

    with caplog.at_level(logging.WARNING):
        run = run_verification(model, registry=registry)
    assert len(run.analyses) == 2  # both executed
    (verdict,) = run.requirements
    assert verdict.status == "pass"  # checked against the FIRST binding (fake)
    assert "multiple bindings" in caplog.text
    apply_results(model, run)
    written = next(
        el for el in model.owned_by(analysis) if getattr(el, "declared_name", "") == "range_km"
    )
    assert "fake==" in written.value.source  # provenance names the checked engine

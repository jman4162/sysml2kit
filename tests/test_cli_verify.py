import json

from typer.testing import CliRunner

from sysml2kit.cli import app
from sysml2kit.interchange import model_to_json
from sysml2kit.model import Model, builder

runner = CliRunner()

ENGINE_MODULE = """
def fake_engine(payload):
    return {"range_km": payload.get("range_km", 420.0)}
"""


def bound_model_file(tmp_path, threshold=400.0):
    model = Model()
    pkg = builder.pkg(model, "Vehicle")
    battery = builder.part(model, "battery", owner=pkg)
    req = builder.req(model, "REQ-001", "Range", owner=pkg, subject=battery)
    builder.attr(model, "metricKey", "range_km", owner=req)
    builder.attr(model, "threshold", threshold, owner=req, unit="km")
    builder.attr(model, "op", ">=", owner=req)
    analysis = builder.analysis(model, "RangeAnalysis", owner=pkg, subject=battery)
    builder.verify(model, source=analysis, target=req, owner=pkg)
    builder.metadata(
        model, analysis, {"engine": "fake", "configRef": "cfg.json"}, name="verificationBinding"
    )
    (tmp_path / "cfg.json").write_text("{}")
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model_to_json(model)))
    return path


def engine_arg(tmp_path, monkeypatch):
    (tmp_path / "fake_engine_mod.py").write_text(ENGINE_MODULE)
    monkeypatch.syspath_prepend(str(tmp_path))
    return "fake=fake_engine_mod:fake_engine"


def test_verify_passes(tmp_path, monkeypatch):
    path = bound_model_file(tmp_path)
    result = runner.invoke(
        app, ["verify", str(path), "--engine", engine_arg(tmp_path, monkeypatch)]
    )
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output
    assert "passed: True" in result.output


def test_verify_fails_on_threshold(tmp_path, monkeypatch):
    path = bound_model_file(tmp_path, threshold=500.0)
    result = runner.invoke(
        app, ["verify", str(path), "--engine", engine_arg(tmp_path, monkeypatch)]
    )
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_verify_report_written(tmp_path, monkeypatch):
    path = bound_model_file(tmp_path)
    report = tmp_path / "run.json"
    result = runner.invoke(
        app,
        [
            "verify",
            str(path),
            "--engine",
            engine_arg(tmp_path, monkeypatch),
            "--report",
            str(report),
        ],
    )
    assert result.exit_code == 0
    data = json.loads(report.read_text())
    assert data["requirements"][0]["status"] == "pass"
    assert data["timestamp"]


def test_verify_write_back_requires_output(tmp_path, monkeypatch):
    path = bound_model_file(tmp_path)
    result = runner.invoke(
        app, ["verify", str(path), "--engine", engine_arg(tmp_path, monkeypatch), "--write-back"]
    )
    assert result.exit_code == 2


def test_verify_write_back(tmp_path, monkeypatch):
    path = bound_model_file(tmp_path)
    out = tmp_path / "annotated.json"
    result = runner.invoke(
        app,
        [
            "verify",
            str(path),
            "--engine",
            engine_arg(tmp_path, monkeypatch),
            "--write-back",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0
    text = out.read_text()
    assert "verificationVerdict" in text
    assert "sysml2kit.verify" in text


def test_verify_missing_engine_fails(tmp_path):
    path = bound_model_file(tmp_path)
    result = runner.invoke(app, ["verify", str(path)])
    assert result.exit_code == 1
    assert "error" in result.output


def test_verify_bad_engine_arg(tmp_path):
    path = bound_model_file(tmp_path)
    result = runner.invoke(app, ["verify", str(path), "--engine", "no-equals-sign"])
    assert result.exit_code == 2


ENGINE_LADDER_MODULE = """
def cheap_engine(payload):
    return {"range_km": 405.0}


def costly_engine(payload):
    return {"range_km": 420.0}
"""


def ladder_model_file(tmp_path):
    model = Model()
    pkg = builder.pkg(model, "Vehicle")
    battery = builder.part(model, "battery", owner=pkg)
    req = builder.req(model, "REQ-001", "Range", owner=pkg, subject=battery)
    builder.attr(model, "metricKey", "range_km", owner=req)
    builder.attr(model, "threshold", 400.0, owner=req, unit="km")
    builder.attr(model, "op", ">=", owner=req)
    analysis = builder.analysis(model, "RangeAnalysis", owner=pkg, subject=battery)
    builder.verify(model, source=analysis, target=req, owner=pkg)
    builder.metadata(
        model,
        analysis,
        {"engine": "cheap", "fidelity": "analytic", "costSeconds": 0.001},
        name="verificationBinding",
    )
    builder.metadata(
        model,
        analysis,
        {"engine": "costly", "fidelity": "pattern", "costSeconds": 0.01},
        name="verificationBinding",
    )
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model_to_json(model)))
    return path


def ladder_engine_args(tmp_path, monkeypatch):
    (tmp_path / "ladder_engine_mod.py").write_text(ENGINE_LADDER_MODULE)
    monkeypatch.syspath_prepend(str(tmp_path))
    return [
        "--engine",
        "cheap=ladder_engine_mod:cheap_engine",
        "--engine",
        "costly=ladder_engine_mod:costly_engine",
    ]


def test_verify_policy_all_shows_rungs(tmp_path, monkeypatch):
    path = ladder_model_file(tmp_path)
    result = runner.invoke(app, ["verify", str(path), *ladder_engine_args(tmp_path, monkeypatch)])
    assert result.exit_code == 0, result.output
    assert "@analytic" in result.output
    assert "@pattern" in result.output
    assert "seconds by fidelity:" in result.output


def test_verify_policy_cheapest_runs_one_rung(tmp_path, monkeypatch):
    path = ladder_model_file(tmp_path)
    result = runner.invoke(
        app,
        ["verify", str(path), *ladder_engine_args(tmp_path, monkeypatch), "--policy", "cheapest"],
    )
    assert result.exit_code == 0, result.output
    assert "@analytic" in result.output
    assert "@pattern" not in result.output


def test_verify_policy_escalate_with_budget(tmp_path, monkeypatch):
    path = ladder_model_file(tmp_path)
    result = runner.invoke(
        app,
        [
            "verify",
            str(path),
            *ladder_engine_args(tmp_path, monkeypatch),
            "--policy",
            "escalate",
            "--budget-s",
            "10",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "(from analytic)" in result.output


def test_verify_fidelity_filter(tmp_path, monkeypatch):
    path = ladder_model_file(tmp_path)
    result = runner.invoke(
        app,
        [
            "verify",
            str(path),
            *ladder_engine_args(tmp_path, monkeypatch),
            "--fidelity",
            "pattern",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "@pattern" in result.output
    assert "@analytic" not in result.output


def test_verify_bad_policy_rejected(tmp_path):
    path = bound_model_file(tmp_path)
    result = runner.invoke(app, ["verify", str(path), "--policy", "fastest"])
    assert result.exit_code == 2

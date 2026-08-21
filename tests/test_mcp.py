import asyncio
import json

import pytest

pytest.importorskip("mcp", reason="mcp extra not installed")

from sysml2kit.interchange import model_to_json
from sysml2kit.mcp import tools_model, tools_requirements
from sysml2kit.mcp.server import get_mcp

EXPECTED_TOOLS = {
    "model_show",
    "model_validate",
    "model_diff",
    "model_export",
    "model_diagram",
    "requirements_trace",
    "requirements_extract",
    "library_load",
}


def write_vehicle(tmp_path, vehicle):
    path = tmp_path / "vehicle.json"
    path.write_text(json.dumps(model_to_json(vehicle)))
    return str(path)


def test_all_tools_registered():
    registered = {t.name for t in asyncio.run(get_mcp().list_tools())}
    assert registered >= EXPECTED_TOOLS


def test_errors_returned_not_raised(tmp_path):
    r = asyncio.run(tools_model.model_validate(str(tmp_path / "missing.json")))
    assert r["status"] == "failed"
    assert "error" in r


def test_path_traversal_rejected():
    r = asyncio.run(tools_model.model_validate("../../etc/passwd"))
    assert r["status"] == "failed"
    assert "traversal" in r["error"]


def test_output_path_traversal_rejected(tmp_path, vehicle):
    r = asyncio.run(tools_model.model_export(write_vehicle(tmp_path, vehicle), "../../evil.json"))
    assert r["status"] == "failed"
    assert "traversal" in r["error"]


def test_model_show(tmp_path, vehicle):
    r = asyncio.run(tools_model.model_show(write_vehicle(tmp_path, vehicle), traceability=True))
    assert r["status"] == "ok"
    assert r["element_count"] == len(vehicle.elements)
    assert "Package: Vehicle" in r["tree"]
    assert "REQ-001" in r["trace_matrix"]


def test_model_validate_reports_issue_counts(tmp_path, vehicle):
    r = asyncio.run(tools_model.model_validate(write_vehicle(tmp_path, vehicle)))
    assert r["status"] == "ok"
    assert r["error_count"] == 0


def test_model_diff(tmp_path, vehicle):
    path = write_vehicle(tmp_path, vehicle)
    r = asyncio.run(tools_model.model_diff(path, path))
    assert r["status"] == "ok"
    assert r["identical"] is True


def test_model_export_writes_artifact(tmp_path, vehicle):
    out = tmp_path / "out" / "v.sysml"
    r = asyncio.run(
        tools_model.model_export(write_vehicle(tmp_path, vehicle), str(out), to="sysml")
    )
    assert r["status"] == "ok"
    assert out.exists()
    assert "package Vehicle {" in out.read_text()


def test_model_diagram_writes_mmd(tmp_path, vehicle):
    out = tmp_path / "trace.mmd"
    r = asyncio.run(tools_model.model_diagram(write_vehicle(tmp_path, vehicle), str(out)))
    assert r["status"] == "ok"
    assert out.read_text().startswith("flowchart LR")


def test_requirements_trace(tmp_path, vehicle):
    r = asyncio.run(tools_requirements.requirements_trace(write_vehicle(tmp_path, vehicle)))
    assert r["status"] == "ok"
    assert r["requirement_count"] == 2
    assert r["unsatisfied"] == ["REQ-001"]
    assert r["unverified"] == ["REQ-002"]


def test_requirements_extract_returns_specs(tmp_path, vehicle):
    r = asyncio.run(tools_requirements.requirements_extract(write_vehicle(tmp_path, vehicle)))
    assert r["status"] == "ok"
    # the vehicle fixture has no metricKey attributes, so zero specs is correct
    assert r["count"] == 0


def test_library_load(tmp_path):
    pytest.importorskip("sysml2kit_rf_library")
    out = tmp_path / "lib.json"
    r = asyncio.run(tools_model.library_load(out=str(out)))
    assert r["status"] == "ok"
    assert out.exists()

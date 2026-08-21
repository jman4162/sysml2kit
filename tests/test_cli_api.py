import json

import httpx
import respx
from typer.testing import CliRunner

from sysml2kit.cli import app
from sysml2kit.interchange import model_to_json

BASE = "https://sysml.example.test"
runner = CliRunner()


@respx.mock
def test_api_projects():
    respx.get(f"{BASE}/projects").mock(
        return_value=httpx.Response(200, json=[{"@id": "p1", "name": "Demo"}])
    )
    result = runner.invoke(app, ["api", "projects", "--url", BASE])
    assert result.exit_code == 0
    assert "p1" in result.output
    assert "Demo" in result.output


@respx.mock
def test_api_pull_latest_commit(tmp_path, vehicle):
    records = model_to_json(vehicle)
    respx.get(f"{BASE}/projects").mock(
        return_value=httpx.Response(200, json=[{"@id": "p1", "name": "Demo"}])
    )
    respx.get(f"{BASE}/projects/p1/commits").mock(
        return_value=httpx.Response(200, json=[{"@id": "c1"}, {"@id": "c2"}])
    )
    respx.get(f"{BASE}/projects/p1/commits/c2/elements").mock(
        return_value=httpx.Response(200, json=records)
    )
    out = tmp_path / "pulled.json"
    result = runner.invoke(app, ["api", "pull", "Demo", "-o", str(out), "--url", BASE])
    assert result.exit_code == 0, result.output
    assert json.loads(out.read_text()) == records


@respx.mock
def test_api_push_with_create(tmp_path, vehicle):
    model_file = tmp_path / "m.json"
    model_file.write_text(json.dumps(model_to_json(vehicle)))
    respx.get(f"{BASE}/projects").mock(return_value=httpx.Response(200, json=[]))
    respx.post(f"{BASE}/projects").mock(
        return_value=httpx.Response(200, json={"@id": "p9", "name": "New"})
    )
    respx.post(f"{BASE}/projects/p9/commits").mock(
        return_value=httpx.Response(200, json={"@id": "c1"})
    )
    result = runner.invoke(
        app, ["api", "push", str(model_file), "--project", "New", "--create", "--url", BASE]
    )
    assert result.exit_code == 0, result.output
    assert "created project p9" in result.output
    assert "commit c1" in result.output


@respx.mock
def test_api_push_unknown_project_without_create(tmp_path, vehicle):
    model_file = tmp_path / "m.json"
    model_file.write_text(json.dumps(model_to_json(vehicle)))
    respx.get(f"{BASE}/projects").mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(
        app, ["api", "push", str(model_file), "--project", "Nope", "--url", BASE]
    )
    assert result.exit_code != 0

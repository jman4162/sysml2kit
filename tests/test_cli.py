import json

from typer.testing import CliRunner

from sysml2kit.cli import app
from sysml2kit.interchange import model_to_json
from sysml2kit.model import Model, builder

runner = CliRunner()


def write_vehicle(tmp_path, vehicle: Model):
    path = tmp_path / "vehicle.json"
    path.write_text(json.dumps(model_to_json(vehicle)))
    return path


def test_show(tmp_path, vehicle):
    result = runner.invoke(app, ["show", str(write_vehicle(tmp_path, vehicle))])
    assert result.exit_code == 0
    assert "Package: Vehicle" in result.output
    assert "PartUsage: battery" in result.output


def test_show_traceability(tmp_path, vehicle):
    result = runner.invoke(app, ["show", str(write_vehicle(tmp_path, vehicle)), "--traceability"])
    assert result.exit_code == 0
    assert "REQ-001" in result.output


def test_validate_ok_is_quietly_clean(tmp_path, vehicle):
    result = runner.invoke(app, ["validate", str(write_vehicle(tmp_path, vehicle))])
    assert result.exit_code == 0


def test_validate_exit_code_on_error(tmp_path, vehicle):
    pkg = vehicle.find(name="Vehicle")[0]
    builder.req(vehicle, "REQ-001", "Duplicate", owner=pkg)
    result = runner.invoke(app, ["validate", str(write_vehicle(tmp_path, vehicle))])
    assert result.exit_code == 1
    assert "S2K002" in result.output


def test_diff_identical(tmp_path, vehicle):
    path = write_vehicle(tmp_path, vehicle)
    result = runner.invoke(app, ["diff", str(path), str(path)])
    assert result.exit_code == 0
    assert "identical" in result.output


def test_diff_nonzero_on_difference(tmp_path, vehicle):
    a = write_vehicle(tmp_path, vehicle)
    pkg = vehicle.find(name="Vehicle")[0]
    builder.part(vehicle, "charger", owner=pkg)
    b = tmp_path / "b.json"
    b.write_text(json.dumps(model_to_json(vehicle)))
    result = runner.invoke(app, ["diff", str(a), str(b)])
    assert result.exit_code == 1
    assert "+ Vehicle::charger" in result.output


def test_export_sysml(tmp_path, vehicle):
    result = runner.invoke(app, ["export", str(write_vehicle(tmp_path, vehicle)), "--to", "sysml"])
    assert result.exit_code == 0
    assert "package Vehicle {" in result.output


def test_export_json_stable_ids_round_trip(tmp_path, vehicle):
    path = write_vehicle(tmp_path, vehicle)
    out = tmp_path / "stable.json"
    first = runner.invoke(
        app, ["export", str(path), "--to", "json", "--stable-ids", "-o", str(out)]
    )
    assert first.exit_code == 0
    text_one = out.read_text()
    second = runner.invoke(
        app, ["export", str(path), "--to", "json", "--stable-ids", "-o", str(out)]
    )
    assert second.exit_code == 0
    assert out.read_text() == text_one  # stable ids => byte-identical exports


def test_unsupported_extension(tmp_path):
    bad = tmp_path / "model.xmi"
    bad.write_text("<xmi/>")
    result = runner.invoke(app, ["show", str(bad)])
    assert result.exit_code != 0

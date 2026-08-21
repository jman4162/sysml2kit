import pytest

pytest.importorskip("sysmlpy")

from typer.testing import CliRunner

from sysml2kit.cli import app

pytestmark = pytest.mark.parse

runner = CliRunner()

CLEAN = """package P {
    part def Widget;
    part b : Widget [2] {
        attribute cap = 5.0 [kg];
    }
    requirement <'R1'> A {
        doc /* the text */
        subject b;
    }
    satisfy A by b;
}
"""

MESSY = CLEAN.replace("    part def", "  part   def").replace(
    "\n    requirement", "\n  requirement"
)

#: Contains a state usage, which the pragmatic profile cannot represent.
LOSSY = """package P {
    part b;
    state charging;
}
"""


def test_fmt_idempotent_on_clean_file(tmp_path):
    f = tmp_path / "m.sysml"
    f.write_text(CLEAN)
    result = runner.invoke(app, ["fmt", str(f)])
    assert result.exit_code == 0
    once = f.read_text()
    result = runner.invoke(app, ["fmt", str(f)])
    assert result.exit_code == 0
    assert f.read_text() == once


def test_fmt_normalizes_messy_whitespace(tmp_path):
    f = tmp_path / "m.sysml"
    f.write_text(MESSY)
    result = runner.invoke(app, ["fmt", str(f)])
    assert result.exit_code == 0
    assert "part def Widget;" in f.read_text()


def test_fmt_refuses_lossy_rewrite(tmp_path):
    f = tmp_path / "m.sysml"
    f.write_text(LOSSY)
    result = runner.invoke(app, ["fmt", str(f)])
    assert result.exit_code == 1
    assert "refusing" in result.output
    assert f.read_text() == LOSSY  # untouched


def test_fmt_lossy_flag_overrides(tmp_path):
    f = tmp_path / "m.sysml"
    f.write_text(LOSSY)
    result = runner.invoke(app, ["fmt", str(f), "--lossy"])
    assert result.exit_code == 0
    assert "state" not in f.read_text()


def test_fmt_check_mode(tmp_path):
    f = tmp_path / "m.sysml"
    f.write_text(MESSY)
    result = runner.invoke(app, ["fmt", str(f), "--check"])
    assert result.exit_code == 1
    assert f.read_text() == MESSY  # check never writes
    runner.invoke(app, ["fmt", str(f)])
    result = runner.invoke(app, ["fmt", str(f), "--check"])
    assert result.exit_code == 0


def test_fmt_output_flag(tmp_path):
    f = tmp_path / "m.sysml"
    out = tmp_path / "out.sysml"
    f.write_text(CLEAN)
    result = runner.invoke(app, ["fmt", str(f), "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert f.read_text() == CLEAN


def test_fmt_rejects_json(tmp_path):
    f = tmp_path / "m.json"
    f.write_text("[]")
    result = runner.invoke(app, ["fmt", str(f)])
    assert result.exit_code != 0


BINDING_BEARING = """package P {
    part b;
    requirement <'R1'> A;
    analysis ana;
    dependency from ana to A; // verify
    metadata verificationBinding about ana {
        engine = "fake";
    }
}
"""


def test_fmt_refuses_binding_bearing_file(tmp_path):
    """Regression: before 0.3.1 fmt silently deleted bindings and verify links.

    Since the fidelity shim, metadata and NAMED dependencies round-trip; an
    unnamed dependency (no verify_/derive_ prefix) still cannot, so fmt must
    refuse this file for that channel.
    """
    f = tmp_path / "m.sysml"
    f.write_text(BINDING_BEARING)
    result = runner.invoke(app, ["fmt", str(f)])
    assert result.exit_code == 1
    assert "refusing" in result.output
    assert "dependency" in result.output
    assert f.read_text() == BINDING_BEARING  # untouched


def test_fmt_accepts_named_dependency_and_metadata(tmp_path):
    """Writer-emitted traceability formats cleanly since the shim."""
    f = tmp_path / "m.sysml"
    f.write_text(
        "package P {\n"
        "    requirement <'R1'> A;\n"
        "    analysis ana;\n"
        "    dependency verify_1 from ana to A;\n"
        '    metadata verificationBinding about ana {\n        engine = "fake";\n    }\n'
        "}\n"
    )
    result = runner.invoke(app, ["fmt", str(f)])
    assert result.exit_code == 0, result.output
    out = f.read_text()
    assert "dependency verify_1 from ana to A;" in out
    assert 'engine = "fake";' in out

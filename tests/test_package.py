from typer.testing import CliRunner

import sysml2kit
from sysml2kit.cli import app


def test_version_is_a_string():
    assert isinstance(sysml2kit.__version__, str)
    assert sysml2kit.__version__


def test_cli_version():
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert sysml2kit.__version__ in result.output

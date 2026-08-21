"""Command line for sysml2kit.

Subcommands ``show``, ``validate``, ``diff``, and ``export`` arrive with the
0.1.0 core; this module currently exposes ``version`` only.
"""

import typer

import sysml2kit

app = typer.Typer(no_args_is_help=True, help=__doc__)


@app.callback()
def main() -> None:
    """Work with SysML v2 models from the command line."""


@app.command()
def version() -> None:
    """Print the installed sysml2kit version."""
    typer.echo(sysml2kit.__version__)


if __name__ == "__main__":
    app()

"""Command line for sysml2kit.

``.json`` inputs are Systems Modeling API interchange files and always work;
``.sysml`` inputs are parsed through the sysmlpy backend, which needs the
``parse`` extra (``pip install sysml2kit[parse]``).
"""

from pathlib import Path
from typing import Annotated

import typer

import sysml2kit
from sysml2kit.model.container import Model

app = typer.Typer(no_args_is_help=True, help=__doc__)


def _load(path: Path) -> Model:
    if path.suffix == ".json":
        from sysml2kit.interchange import model_from_json

        return model_from_json(path)
    if path.suffix == ".sysml":
        from sysml2kit.backends import get_backend

        return get_backend("sysmlpy").parse(path.read_text(), filename=str(path))
    raise typer.BadParameter(f"unsupported file type: {path} (expected .json or .sysml)")


@app.callback()
def main() -> None:
    """Work with SysML v2 models from the command line."""


@app.command()
def version() -> None:
    """Print the installed sysml2kit version."""
    typer.echo(sysml2kit.__version__)


@app.command()
def show(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    traceability: Annotated[
        bool, typer.Option("--traceability", help="Print the requirement-to-part trace matrix.")
    ] = False,
) -> None:
    """Print the element tree (and optionally the trace matrix) of a model file."""
    model = _load(file)
    counts: dict[str, int] = {}
    for element in model.iter_elements():
        counts[type(element).__name__] = counts.get(type(element).__name__, 0) + 1
        depth = 0
        current = model.owner.get(element.element_id)
        while current is not None:
            depth += 1
            current = model.owner.get(current)
        typer.echo("    " * depth + f"{type(element).__name__}: {element.label}")
    typer.echo("")
    typer.echo(", ".join(f"{n} {k}" for k, n in sorted(counts.items())))
    if traceability:
        from sysml2kit.query import trace_matrix

        typer.echo("")
        typer.echo(trace_matrix(model).render())


@app.command()
def validate(
    files: Annotated[list[Path], typer.Argument(exists=True, dir_okay=False)],
) -> None:
    """Validate model files; exits 1 if any error-severity issue is found."""
    from sysml2kit.validation import validate as run_rules

    worst_is_error = False
    for file in files:
        issues = run_rules(_load(file))
        if not issues:
            typer.echo(f"{file}: ok")
            continue
        for issue in issues:
            typer.echo(f"{file}: {issue.severity} {issue.rule_id}: {issue.message}")
            worst_is_error = worst_is_error or issue.severity == "error"
    if worst_is_error:
        raise typer.Exit(code=1)


@app.command()
def diff(
    file_a: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    file_b: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    by_name: Annotated[
        bool,
        typer.Option("--by-name", help="Match elements by qualified name instead of element id."),
    ] = False,
) -> None:
    """Print the element-level differences between two model files."""
    from sysml2kit.diff import diff_models, render_diff

    entries = diff_models(_load(file_a), _load(file_b), by_name=by_name)
    typer.echo(render_diff(entries))
    if entries:
        raise typer.Exit(code=1)


@app.command()
def fmt(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output file (default: rewrite in place).")
    ] = None,
    check: Annotated[
        bool, typer.Option("--check", help="Exit 1 if the file would change; write nothing.")
    ] = False,
    lossy: Annotated[
        bool,
        typer.Option("--lossy", help="Format even when the rewrite would lose content."),
    ] = False,
) -> None:
    """Reformat a .sysml file through the writer, refusing lossy rewrites.

    Safety gate: the input and the formatted output are both re-parsed; a
    grammar-node count mismatch or a model-level diff means the rewrite would
    drop content, and fmt refuses unless --lossy is passed.
    """
    if file.suffix != ".sysml":
        raise typer.BadParameter("fmt operates on .sysml files")
    from sysml2kit.backends import get_backend
    from sysml2kit.backends.sysmlpy import grammar_signature
    from sysml2kit.diff import diff_models, render_diff
    from sysml2kit.text import write_model

    source = file.read_text()
    backend = get_backend("sysmlpy")
    model = backend.parse(source, filename=str(file))
    formatted = write_model(model)

    losses: list[str] = []
    before, after = grammar_signature(source), grammar_signature(formatted)
    for kind in sorted(set(before) | set(after)):
        if before.get(kind, 0) != after.get(kind, 0):
            losses.append(f"{kind}: {before.get(kind, 0)} -> {after.get(kind, 0)}")
    entries = diff_models(model, backend.parse(formatted), by_name=True)
    if entries:
        losses.append(render_diff(entries))
    if losses and not lossy:
        typer.echo(f"{file}: refusing to format, the rewrite would change content:")
        for loss in losses:
            typer.echo(f"  {loss}")
        typer.echo("Pass --lossy to format anyway.")
        raise typer.Exit(code=1)

    if check:
        if formatted != source:
            typer.echo(f"{file}: would be reformatted")
            raise typer.Exit(code=1)
        typer.echo(f"{file}: already formatted")
        return
    target = output or file
    target.write_text(formatted)
    typer.echo(f"wrote {target}")


@app.command()
def export(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    to: Annotated[str, typer.Option("--to", help="Output format: json or sysml.")] = "json",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output file (default: stdout).")
    ] = None,
    stable_ids: Annotated[
        bool,
        typer.Option("--stable-ids", help="Rewrite ids as UUIDv5 name hashes before export."),
    ] = False,
) -> None:
    """Convert a model file to interchange JSON or textual notation."""
    model = _load(file)
    if stable_ids:
        model.assign_stable_ids()
    if to == "json":
        import json

        from sysml2kit.interchange import model_to_json

        text = json.dumps(model_to_json(model), indent=2) + "\n"
    elif to == "sysml":
        from sysml2kit.text import write_model

        text = write_model(model)
    else:
        raise typer.BadParameter("--to must be 'json' or 'sysml'")
    if output is None:
        typer.echo(text, nl=False)
    else:
        output.write_text(text)
        typer.echo(f"wrote {output}")


if __name__ == "__main__":
    app()

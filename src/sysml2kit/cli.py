"""Command line for sysml2kit.

``.json`` inputs are Systems Modeling API interchange files and always work;
``.sysml`` inputs are parsed through the sysmlpy backend, which needs the
``parse`` extra (``pip install sysml2kit[parse]``).
"""

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

import sysml2kit
from sysml2kit.model.container import Model

if TYPE_CHECKING:
    from sysml2kit.api import Project, SysMLApiClient

app = typer.Typer(no_args_is_help=True, help=__doc__)
mcp_app = typer.Typer(help="MCP server (needs the mcp extra).")
app.add_typer(mcp_app, name="mcp")
api_app = typer.Typer(help="Talk to a Systems Modeling API server.")
app.add_typer(api_app, name="api")

UrlOption = Annotated[
    str,
    typer.Option("--url", envvar="SYSML2KIT_API_URL", help="Server base URL."),
]
TokenOption = Annotated[
    str | None,
    typer.Option("--token", envvar="SYSML2KIT_API_TOKEN", help="Bearer token."),
]


def _api_client(url: str, token: str | None) -> "SysMLApiClient":
    from sysml2kit.api import SysMLApiClient

    return SysMLApiClient(url, token=token)


def _resolve_project(client: "SysMLApiClient", name_or_id: str) -> "Project":
    projects = client.list_projects()
    exact = [p for p in projects if p.id == name_or_id]
    if exact:
        return exact[0]
    named = [p for p in projects if p.name == name_or_id]
    if len(named) == 1:
        return named[0]
    if not named:
        raise typer.BadParameter(f"no project named {name_or_id!r}")
    raise typer.BadParameter(f"project name {name_or_id!r} is ambiguous; use the id")


@api_app.command("projects")
def api_projects(url: UrlOption, token: TokenOption = None) -> None:
    """List projects on the server."""
    with _api_client(url, token) as client:
        for project in client.list_projects():
            typer.echo(f"{project.id}  {project.name or ''}")


@api_app.command("pull")
def api_pull(
    project: Annotated[str, typer.Argument(help="Project id or unique name.")],
    commit: Annotated[str | None, typer.Argument(help="Commit id (default: newest).")] = None,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("model.json"),
    url: UrlOption = "",
    token: TokenOption = None,
) -> None:
    """Download a commit's elements as interchange JSON."""
    import json

    from sysml2kit.interchange import model_to_json

    with _api_client(url, token) as client:
        resolved = _resolve_project(client, project)
        commit_id = commit or client.head_commit(resolved.id).id
        model = client.list_elements(resolved.id, commit_id)
    output.write_text(json.dumps(model_to_json(model), indent=2) + "\n")
    typer.echo(f"wrote {output} ({len(model.elements)} elements from commit {commit_id})")


@api_app.command("push")
def api_push(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    project: Annotated[str, typer.Option("--project", help="Project id or unique name.")],
    create: Annotated[
        bool, typer.Option("--create", help="Create the project when the name is unknown.")
    ] = False,
    message: Annotated[str | None, typer.Option("--message", "-m")] = None,
    url: UrlOption = "",
    token: TokenOption = None,
) -> None:
    """Push a model file to the server as a new commit."""
    model = _load(file)
    with _api_client(url, token) as client:
        try:
            resolved = _resolve_project(client, project)
        except typer.BadParameter:
            if not create:
                raise
            resolved = client.create_project(project)
            typer.echo(f"created project {resolved.id}")
        commit = client.push_model(resolved.id, model, message=message)
    typer.echo(f"pushed {len(model.elements)} elements as commit {commit.id}")


@mcp_app.command()
def serve(
    transport: Annotated[
        str, typer.Option("--transport", help="Transport: stdio or http.")
    ] = "stdio",
) -> None:
    """Run the sysml2kit MCP server."""
    if transport not in ("stdio", "http"):
        raise typer.BadParameter("transport must be 'stdio' or 'http'")
    from sysml2kit.mcp.server import run_server

    run_server(transport="streamable-http" if transport == "http" else "stdio")


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
def verify(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    engine: Annotated[
        list[str] | None,
        typer.Option(
            "--engine",
            help="Extra engine as name=module:function (operator input; repeatable).",
        ),
    ] = None,
    analysis: Annotated[
        list[str] | None,
        typer.Option("--analysis", help="Only run these analyses (qualified names; repeatable)."),
    ] = None,
    report: Annotated[
        Path | None, typer.Option("--report", help="Write the VerificationRun JSON here.")
    ] = None,
    write_back: Annotated[
        bool, typer.Option("--write-back", help="Record results into the model (needs -o).")
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Updated model JSON for --write-back.")
    ] = None,
) -> None:
    """Run bound analyses and check the requirements they verify.

    Exit codes: 0 all must-requirements pass; 1 a must-requirement failed or
    an engine errored; 2 usage errors.
    """
    from datetime import UTC, datetime

    from sysml2kit.verify import EngineRegistry, apply_results, run_verification

    if write_back and output is None:
        raise typer.BadParameter("--write-back needs -o/--output")
    registry = EngineRegistry.discover()
    for item in engine or []:
        if "=" not in item or ":" not in item.split("=", 1)[1]:
            raise typer.BadParameter(f"--engine {item!r}: expected name=module:function")
        name, target = item.split("=", 1)
        module_name, func_name = target.split(":", 1)
        import importlib

        registry.register(name, getattr(importlib.import_module(module_name), func_name))

    model = _load(file)
    run = run_verification(
        model,
        model_path=file,
        registry=registry,
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        analyses=analysis,
    )

    for result in run.analyses:
        state = f"error: {result.error}" if result.error else f"{len(result.metrics)} metrics"
        typer.echo(f"analysis {result.analysis} [{result.engine}]: {state}")
    for v in run.requirements:
        threshold = f"{v.op} {v.threshold}" if v.op is not None else "(no threshold)"
        actual = "-" if v.actual is None else f"{v.actual:g}"
        margin = "-" if v.margin is None else f"{v.margin:+g}"
        typer.echo(
            f"{v.status.upper():7s} {v.requirement_id:20s} {v.metric_key:40s} "
            f"{threshold:12s} actual={actual} margin={margin} [{v.severity}]"
        )
    typer.echo(f"passed: {run.passed}")

    if report is not None:
        report.write_text(run.model_dump_json(indent=2) + "\n")
        typer.echo(f"wrote {report}")
    if write_back and output is not None:
        import json as json_module

        from sysml2kit.interchange import model_to_json

        apply_results(model, run)
        output.write_text(json_module.dumps(model_to_json(model), indent=2) + "\n")
        typer.echo(f"wrote {output}")
    if not run.passed:
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
    to: Annotated[
        str, typer.Option("--to", help="Output format: json, sysml, or mermaid.")
    ] = "json",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output file (default: stdout).")
    ] = None,
    stable_ids: Annotated[
        bool,
        typer.Option("--stable-ids", help="Rewrite ids as UUIDv5 name hashes before export."),
    ] = False,
    diagram: Annotated[
        str,
        typer.Option("--diagram", help="Mermaid view: trace (default) or tree."),
    ] = "trace",
) -> None:
    """Convert a model file to interchange JSON, textual notation, or a mermaid diagram."""
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
    elif to == "mermaid":
        from sysml2kit.views import to_mermaid_trace, to_mermaid_tree

        if diagram == "trace":
            text = to_mermaid_trace(model)
        elif diagram == "tree":
            text = to_mermaid_tree(model)
        else:
            raise typer.BadParameter("--diagram must be 'trace' or 'tree'")
    else:
        raise typer.BadParameter("--to must be 'json', 'sysml', or 'mermaid'")
    if output is None:
        typer.echo(text, nl=False)
    else:
        output.write_text(text)
        typer.echo(f"wrote {output}")


if __name__ == "__main__":
    app()

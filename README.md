# sysml2kit

[![CI](https://github.com/jman4162/sysml2kit/actions/workflows/ci.yml/badge.svg)](https://github.com/jman4162/sysml2kit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sysml2kit)](https://pypi.org/project/sysml2kit/)
[![Python](https://img.shields.io/pypi/pyversions/sysml2kit)](https://pypi.org/project/sysml2kit/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-jman4162.github.io-blue)](https://jman4162.github.io/sysml2kit/)

API-first Python tooling for building, querying, validating, and automating
SysML v2 models.

> **Status: pre-alpha.** The 0.4.x line covers the full loop: model, writer,
> interchange, queries, validation, diff, mermaid views, parse backend, MCP
> server, API client with a live-server harness, and multi-fidelity
> verification execution. The API may still move between minor versions; pin
> an exact version if you depend on it. Changes: [CHANGELOG.md](CHANGELOG.md).

`sysml2kit` is the requirements/architecture/traceability layer for
engineering automation stacks: build a system model in Python, emit standard
SysML v2 textual notation and Systems Modeling API JSON, run traceability
queries (which requirements are unsatisfied? unverified? allocated where?),
validate, diff, and **execute verification**: analyses bound to registered
engines run for real, and their metrics check the model's requirements. It
targets the OMG SysML v2 standard, not any vendor tool. Docs:
https://jman4162.github.io/sysml2kit/

## What it does

- **Object model**: a documented subset of SysML v2 (packages, parts, ports,
  attributes with units, requirements, satisfy/verify/derive/allocate,
  analysis cases) as pydantic models, with an opaque passthrough for elements
  outside the subset so richer models survive a round trip.
- **Textual notation writer**: deterministic `.sysml` output. Parsing is
  delegated to a pluggable backend (`pip install sysml2kit[parse]` installs
  [sysmlpy](https://github.com/mycr0ft/sysmlpy)); the kit itself does not
  reimplement the grammar.
- **JSON interchange**: read/write the Systems Modeling API serialization,
  the format the standard REST API speaks.
- **Traceability queries**: unsatisfied/unverified requirements, allocation
  tables, requirement-to-part trace matrices.
- **Validation and diff**: rule-based model checks and element-level diffs.
- **Verification execution**: `verificationBinding` metadata binds an
  analysis case to an engine from the `sysml2kit.engines` entry-point group;
  `sysml2kit verify` runs it and checks each requirement with margins, and
  can write results back into the model with provenance. Sibling bindings
  labeled with `fidelity`/`costSeconds` form a fidelity ladder: `--policy
  all` reports the cross-rung spread as an error bar, `--policy escalate
  --budget-s N` spends a compute budget on the thinnest margins first, and
  every run records measured seconds per rung. The whole loop — bindings,
  verify links, policies — works from `.sysml` text as well as JSON.
- **Mermaid views**: ownership-tree and requirement-trace diagrams.
- **MCP server**: nine tools for agents (`sysml2kit mcp serve`).
- **API client**: a thin HTTP client for the OMG Systems Modeling API and
  Services endpoints, plus a docker compose harness running the pilot
  implementation for live round-trip testing.

## Install

```bash
pip install sysml2kit            # core: build, write, query, validate, diff
pip install "sysml2kit[parse]"   # + read .sysml files (sysmlpy backend)
pip install "sysml2kit[graph]"   # + NetworkX export
pip install "sysml2kit[mcp]"     # + MCP server for agents
pip install "sysml2kit[verify]"  # + YAML verification-binding configs
```

## Quick start

```python
from sysml2kit import Model, builder

model = Model()
pkg = builder.pkg(model, "Vehicle")
battery = builder.part(model, "battery", owner=pkg)
range_req = builder.req(
    model,
    "REQ-001",
    "Range",
    owner=pkg,
    text="The vehicle shall travel at least 400 km on one charge.",
)
builder.satisfy(model, source=battery, target=range_req)

from sysml2kit.text import write_model

print(write_model(model))  # standard SysML v2 textual notation

from sysml2kit.query import unverified_requirements

print(unverified_requirements(model))  # [REQ-001] — no verify link yet
```

## Architecture

```
sysml2kit
├── model         # element classes, Model container, builder API
├── text          # SysML v2 textual notation writer
├── interchange   # Systems Modeling API JSON reader/writer
├── query         # traceability queries
├── validation    # rule-based checks (S2K001...)
├── diff          # element-level model diff
├── views         # mermaid diagrams (trace, tree)
├── verify        # verification bindings, engine registry, runner
├── api           # Systems Modeling API HTTP client
├── backends      # parser backends (sysmlpy behind the [parse] extra)
├── interop       # tool-agnostic requirement extraction
├── mcp           # MCP server (behind the [mcp] extra)
├── graph, units, workspace   # NetworkX export, pint helpers, path safety
└── cli           # `sysml2kit` command line
```

The spec pin, element subset, and known deviations are documented in
[SPEC.md](SPEC.md). Reference spec release: OMG `SysML-v2-Release` tag
`2026-05`.

Domain content lives outside the kit. For antenna/RF systems engineering, see
[sysml2kit-rf-library](https://github.com/jman4162/sysml2kit-rf-library), a
SysML v2 model library consumed through this package. Downstream bridges are
merged in [phased-array-systems](https://github.com/jman4162/phased-array-systems)
(`interop.sysml`: requirement sets and the `phased-array-systems` verification
engine) and [aedl](https://github.com/jman4162/aedl-electromagnetic-design-agent)
(`aedl.interop`: bound-form requirements).

## For agents

An MCP server ships behind the `mcp` extra with nine tools: `model_show`,
`model_validate`, `model_diff`, `model_export`, `model_diagram`,
`requirements_trace`, `requirements_extract`, `requirements_verify`, `library_load`. Artifacts are
returned as file paths, not payloads.

```bash
pip install "sysml2kit[mcp,parse]"
sysml2kit mcp serve            # stdio; --transport http also supported
```

```json
{"mcpServers": {"sysml2kit": {"command": "sysml2kit", "args": ["mcp", "serve"]}}}
```

The CLI covers the same operations for shell use:
`sysml2kit show | validate | diff | export | fmt | verify | api | mcp serve`
(`export --to mermaid` renders diagrams).

## Development

```bash
uv sync --all-extras --group dev
uv run pytest                     # core suite (no extras needed)
uv run pytest -m parse            # round-trip tests against sysmlpy
uv run ruff check . && uv run ruff format --check .
uv run mypy
scripts/slopcheck.sh              # prose lint, advisory
uv run mkdocs serve               # docs preview
```

## Citation

```bibtex
@software{hodge2026sysml2kit,
  author  = {Hodge, John},
  title   = {sysml2kit: API-first Python tooling for SysML v2 models},
  year    = {2026},
  url     = {https://github.com/jman4162/sysml2kit},
  license = {Apache-2.0}
}
```

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). This project contains
no code or model text from the EPL-2.0 OMG pilot implementation; conformance
checks run it out of process only.

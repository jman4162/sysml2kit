# sysml2kit

[![CI](https://github.com/jman4162/sysml2kit/actions/workflows/ci.yml/badge.svg)](https://github.com/jman4162/sysml2kit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sysml2kit)](https://pypi.org/project/sysml2kit/)
[![Python](https://img.shields.io/pypi/pyversions/sysml2kit)](https://pypi.org/project/sysml2kit/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

API-first Python tooling for building, querying, validating, and automating
SysML v2 models.

> **Status: pre-alpha.** The 0.1.x line has a working core (model, writer,
> interchange, queries, validation, diff, API client, parse backend); the API
> may still move between minor versions. Pin an exact version if you depend
> on it.

`sysml2kit` is the requirements/architecture/traceability layer for
engineering automation stacks: build a system model in Python, emit standard
SysML v2 textual notation and Systems Modeling API JSON, run traceability
queries (which requirements are unsatisfied? unverified? allocated where?),
validate, and diff. It targets the OMG SysML v2 standard, not any vendor tool.

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
- **API client**: a thin HTTP client for the OMG Systems Modeling API and
  Services endpoints.

## Install

```bash
pip install sysml2kit            # core: build, write, query, validate, diff
pip install "sysml2kit[parse]"   # + read .sysml files (sysmlpy backend)
pip install "sysml2kit[graph]"   # + NetworkX export
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
├── api           # Systems Modeling API HTTP client
├── backends      # parser backends (sysmlpy behind the [parse] extra)
├── interop       # tool-agnostic requirement extraction
└── cli           # `sysml2kit` command line
```

The spec pin, element subset, and known deviations are documented in
[SPEC.md](SPEC.md). Reference spec release: OMG `SysML-v2-Release` tag
`2026-05`.

Domain content lives outside the kit. For antenna/RF systems engineering, see
[sysml2kit-rf-library](https://github.com/jman4162/sysml2kit-rf-library), a
SysML v2 model library consumed through this package.

## For agents

An MCP server ships behind the `mcp` extra with eight tools: `model_show`,
`model_validate`, `model_diff`, `model_export`, `model_diagram`,
`requirements_trace`, `requirements_extract`, `library_load`. Artifacts are
returned as file paths, not payloads.

```bash
pip install "sysml2kit[mcp,parse]"
sysml2kit mcp serve            # stdio; --transport http also supported
```

```json
{"mcpServers": {"sysml2kit": {"command": "sysml2kit", "args": ["mcp", "serve"]}}}
```

The CLI (`sysml2kit show | validate | diff | export | fmt`) covers the same
operations for shell use.

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

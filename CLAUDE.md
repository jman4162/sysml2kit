# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`sysml2kit` is an Apache-2.0 Python toolkit for building, querying, validating,
and automating SysML v2 models. It is domain-general: no RF/antenna types in
the API. Domain content lives in the companion repo `sysml2kit-rf-library`.
Positioning: the requirements/architecture/traceability layer above
`phased-array-systems` in the agentic RF design stack.

Reference spec: OMG `SysML-v2-Release` tag `2026-05` (pinned in SPEC.md).
The kit implements a documented ~20-element "pragmatic profile" plus an
`OpaqueElement` passthrough — never claim full abstract-syntax coverage.

## Commands

```bash
uv sync --all-extras --group dev          # set up
uv run pytest                             # core suite (markers parse/api/conformance excluded by -m in CI)
uv run pytest -m parse                    # needs the sysmlpy extra (installed via --all-extras)
uv run pytest tests/test_model.py -k name # single test
uv run ruff check . && uv run ruff format --check .
uv run mypy
scripts/slopcheck.sh                      # prose lint (advisory; --strict for CI behavior)
uv run mkdocs build --strict              # docs
pre-commit run --all-files
```

Release: tag `vX.Y.Z` and push; `release.yml` publishes to PyPI via Trusted
Publishing (environment `pypi`). Version comes from git tags (hatch-vcs);
never edit `_version.py` or add a version literal.

## Architecture

- `model/` — pydantic element classes (structure, requirements, relations,
  analysis, metadata), `Ref` (UUID cross-references, never direct object
  refs), `Model` container (identity/ownership registry, `assign_stable_ids()`
  for diffable exports), `builder` (fluent authoring API).
- `text/` — deterministic `.sysml` writer. There is NO parser in this repo by
  design; parsing goes through `backends/` (sysmlpy behind the `[parse]`
  extra). Do not add grammar code.
- `interchange/` — Systems Modeling API JSON reader/writer; `typemap.py` is
  the single point of spec-version coupling. Unknown `@type` → `OpaqueElement`
  with the raw record preserved.
- `query.py` / `validation.py` (rule ids `S2K001…`) / `diff.py`.
- `api/` — hand-written httpx client for the Systems Modeling API. Do not
  introduce generated clients (the official generated one is LGPL).
- `interop/` — `RequirementSpec` extraction; the `metricKey` attribute
  convention bridges to phased-array-systems and aedl (adapters live in those
  repos, not here).
- `cli.py` — typer app. MCP is deferred to v0.2; when added it goes in
  `src/sysml2kit/mcp/` following apab's `docs/mcp-conventions.md`.

## Constraints

- **License hygiene**: never paste code or model text from the OMG
  pilot-implementation / Release repos (EPL-2.0) into this Apache-2.0 repo.
  The conformance oracle (`tools/conformance/`) downloads the pilot jar at CI
  runtime and runs it out of process only.
- **Prose rule**: every piece of prose (README, docs, docstrings, commit
  messages) must pass `scripts/slopcheck.sh` (slopscore-lint, profile
  `technical`). Invoke slopscore via `uvx --from slopscore-lint slopscore-lint`
  — the pyenv-shimmed global install is stale.
- Commit as John Hodge / jman4162 / jhodge007@gmail.com (never jah70@vt.edu).
- macOS/iCloud gotcha: symlink `.venv → ~/.venvs/sysml2kit`; a real `.venv`
  under `~/Documents` breaks editable installs when iCloud hides `.pth` files.
- `*.local.md` files are private notes and stay untracked.

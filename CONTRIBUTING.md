# Contributing

## Setup

```bash
git clone git@github.com:jman4162/sysml2kit.git
cd sysml2kit
uv sync --all-extras --group dev
pre-commit install
```

## Checks that gate a merge

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run mkdocs build --strict
```

`scripts/slopcheck.sh` (prose lint) is advisory; review its findings but a
merge is never gated on it.

## License hygiene

This repo is Apache-2.0. The OMG pilot implementation and the
`SysML-v2-Release` repository (including the normative model libraries and
grammar files) are EPL-2.0. **Do not paste code, grammar text, or model-library
text from those repositories into this one.** The conformance workflow runs
the pilot jar out of process and never commits it. Reference standard library
symbols (ISQ, SI) by import name only.

## Conventions

- Version comes from git tags via hatch-vcs; never hand-edit a version.
- Parsing goes through `sysml2kit.backends`; no grammar code in this repo.
- `interchange/typemap.py` is the only module allowed to hard-code spec
  `@type` strings.
- Validation rules get the next free `S2K` id and a docs entry.
- New public API needs a docstring, a test, and a docs mention in the same PR.

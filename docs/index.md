# sysml2kit

API-first Python tooling for building, querying, validating, and automating
SysML v2 models.

```bash
pip install sysml2kit            # build, write, query, validate, diff
pip install "sysml2kit[parse]"   # + read .sysml files (sysmlpy backend)
```

`sysml2kit` is the requirements/architecture/traceability layer for
engineering automation stacks: build a system model in Python, emit standard
SysML v2 textual notation and Systems Modeling API JSON, answer traceability
questions (which requirements are unsatisfied? unverified? allocated where?),
validate, and diff.

Reference spec release: OMG `SysML-v2-Release` tag `2026-05`. The element
subset and known deviations are documented in
[concepts](concepts.md) and the repo's `SPEC.md`.

Start with the [quickstart](quickstart.md), then the
[traceability](traceability.md) page — the queries there are the point of the
package. For antenna/RF domain content, see
[the RF library](rf-library.md).

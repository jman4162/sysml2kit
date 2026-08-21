# Changelog

## 0.1.0 — 2026-08-21

First working release.

- Object model: the pragmatic profile (~20 element kinds) as pydantic
  classes, `Model` container with identity/ownership/qualified names,
  `assign_stable_ids()` (UUIDv5), fluent builder API, `AttributeValue` with
  unit text and provenance, pint-backed unit helpers.
- JSON interchange: Systems Modeling API serialization reader/writer,
  deterministic output, `OpaqueElement` passthrough for unknown `@type`s;
  json→model→json fixpoint property-tested.
- Textual notation writer: deterministic `.sysml` output; verified against
  the sysmlpy parser (write → parse → structural compare).
- Traceability queries: satisfied_by/verified_by/derived_from,
  unsatisfied/unverified requirements, allocation table, trace matrix.
- Validation: rules S2K001–S2K009 with severities and stable ids.
- Diff: element-level with `--by-name` matching for regenerated ids.
- API client: hand-written httpx client for the Systems Modeling API
  (projects/branches/commits/elements reads, create_project, push_model).
- Parser backends: `ParserBackend` protocol; sysmlpy adapter behind the
  `parse` extra.
- Interop: `extract_requirements` reading the metricKey convention, with
  dual-form thresholds for operator-style and bound-style engines.
- CLI: `show` (`--traceability`), `validate`, `diff`, `export`
  (`--stable-ids`), `version`.
- Docs site, conformance-oracle workflow scaffold, prose lint tooling.

## 0.0.1 — 2026-08-21

- Package skeleton published to claim the PyPI name. Importable, no usable
  functionality yet.

# Changelog

## 0.3.0 — 2026-08-21

- **Verification execution** (`sysml2kit.verify`): `verificationBinding`
  metadata binds an analysis case to an engine resolved by name from the
  `sysml2kit.engines` entry-point group (model text never names code paths).
  `run_verification` executes bound analyses and checks each metricKey
  requirement with margins; `apply_results` writes metrics and verdicts back
  into the model with provenance, idempotently. CLI `sysml2kit verify`, MCP
  tool `requirements_verify` (nine tools now), `verify` extra for YAML
  configs, and a `docs/verification.md` flagship page. First engine:
  phased-array-systems (PR #2 there).
- **Live-server harness**: `docker/compose.yaml` runs the pilot
  implementation (digest-pinned) + postgres; `api`-marked round-trip tests
  pass against the real server; weekly advisory `live-api` workflow. Live
  testing hardened the client and reader for the pilot dialect: list-typed
  endpoints/typing/text adapted on push and tolerated on read, verify/derive
  pushed as Dependency, multiplicity/doc dropped by the server, server-minted
  element ids; known-@type records that do not fit the profile now degrade to
  OpaqueElement instead of failing the read.
- **`api` CLI group**: `projects`, `pull` (newest commit by default),
  `push --create`; `SYSML2KIT_API_URL`/`SYSML2KIT_API_TOKEN` env vars;
  `SysMLApiClient.head_commit`.
- **Diagrams docs page** and a README refresh for the 0.3 surface.
- Upstream sysmlpy fixes submitted for the two pinned parse losses:
  dependency statements (mycr0ft/sysmlpy#7) and allocate endpoints
  (mycr0ft/sysmlpy#6).

## 0.2.0 — 2026-08-21

- **Parse fidelity**: the sysmlpy backend now walks the raw ANTLR dict
  (`load_grammar_antlr`) instead of the lossy wrapper objects. Short names,
  feature typing (incl. cross-package), multiplicity, attribute values with
  units, requirement subjects and text, docs, and satisfy statements survive
  a text parse. Upstream visitor losses (dependency statements, allocate and
  connect endpoints, verification cases) are pinned by tests, documented in
  SPEC.md, and filed upstream (sysmlpy #4, #5).
- **MCP server** (`pip install sysml2kit[mcp]`; `sysml2kit mcp serve`):
  eight tools — model_show, model_validate, model_diff, model_export,
  model_diagram, requirements_trace, requirements_extract, library_load.
- **`fmt` command** with a loss-refusing safety gate (grammar-signature and
  model-diff comparison; `--lossy` to override, `--check` for CI).
- **Mermaid views** (`sysml2kit.views`): ownership tree and requirement
  trace diagrams; `export --to mermaid` and the model_diagram tool.
- **Conformance oracle** pinned to windtrader-java 0.1.1 (sha256-verified,
  out-of-process pilot parser); weekly workflow green.
- Downstream bridges landed as PRs: phased-array-systems#1 (op-form
  RequirementSet) and aedl#1 (bound-form requirements); the RequirementSpec
  field set is now frozen by a schema test.

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

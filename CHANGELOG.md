# Changelog

## 0.4.0 — 2026-08-21

The multi-fidelity release: one analysis, several engines, honest error
bars, and budgeted escalation — from JSON or from the textual notation.

- **Fidelity ladders.** An analysis may carry sibling
  `verificationBinding` annotations labeled by two new reserved keys,
  `fidelity` (rung name) and `costSeconds` (declared wall-clock, which
  orders the ladder). Sibling bindings are named metadata usages typed
  by a `metadata def verificationBinding` (`builder.metadata_def` +
  `builder.metadata(..., definition=...)`), since distinct names are
  what stable-id hashing needs; a single binding may still just be named
  `verificationBinding`. Validation rule S2K010 rejects duplicate rung
  labels and warns on mixed labeled/unlabeled siblings.
- **Runner policies.** `run_verification(..., policy=...)`: `all`
  (default) runs every rung and reports the cross-rung `spread` per
  requirement; `cheapest` runs one; `escalate` runs the cheapest rungs,
  ranks must-requirements by margin thinness, and escalates within
  `budget_s` against declared costs (verdicts carry `escalated_from`).
  Every run records measured `seconds_by_fidelity`; write-back uses the
  highest-fidelity verdict and names the rung in its provenance. CLI:
  `verify --policy/--budget-s/--fidelity`; MCP `requirements_verify`
  gains `policy`/`budget_s` and returns `seconds_by_fidelity`.
- **Text notation carries the whole loop.** A guarded runtime shim
  (`backends/_sysmlpy_patches.py`, mirroring upstream mycr0ft/sysmlpy
  #6, #7, and #9) fixes three visitor defects, and the writer emits
  named dependencies (`dependency verify_1 from A to B;`), typed
  bindings, and package-level metadata — so satisfy, verify, derive,
  allocate, and bindings all round-trip through `.sysml` text.
  `sysml2kit verify` accepts several text files parsed as one model
  (the file declaring the `metadata def` rides along) and warns instead
  of passing vacuously when no bindings are found.
- **Ownership survives the pilot server.** `push_model` runs in two
  phases (elements with `aliasIds`, then `OwningMembership` records
  mapped through server-minted ids); the interchange reader folds
  membership records back into the owner map. New `api branches` and
  `api commits` subcommands.
- Pins: sysmlpy floor 0.36.3; the hatchling `<1.32` cap is lifted
  (Metadata-Version 2.5 passes current twine); the 2026-05 spec pin was
  re-confirmed as newest on 2026-08-21.

## 0.3.1 — 2026-08-21

Hotfix release; upgrade recommended.

- **`fmt` could silently delete verification bindings and verify links.**
  The loss gate's grammar signature missed MetadataFeature nodes, and
  dependency statements leave no grammar node at all, so a format pass on a
  binding-bearing file removed both without triggering the refusal. The
  signature now covers metadata/annotation/dependency nodes and a textual
  keyword guard catches statements the parser drops entirely; `fmt` on such
  files now refuses unless `--lossy` is passed.
- Metadata values in textual output were rendered with Python repr
  (single-quoted strings, `True`/`False`); they now render as SysML text
  (double-quoted strings, `true`/`false`).
- With multiple verificationBinding annotations on one analysis, requirement
  checking used the last binding while write-back provenance named the
  first. Both now use the first binding, extra bindings execute with a
  logged warning, and full multi-binding support is planned.

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

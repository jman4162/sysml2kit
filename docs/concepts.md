# Concepts

## The pragmatic profile

sysml2kit implements ~20 element kinds (packages, part/port/attribute
definitions and usages, interfaces, connections, requirements, constraints,
analysis cases, metadata, and four traceability relationships), not the full
~270-metaclass abstract syntax. Anything outside the profile round-trips
through `OpaqueElement`: on JSON import an unrecognized `@type` keeps its raw
record and ownership links, and re-exports unchanged.

The repo's `SPEC.md` lists the profile, the pinned spec release
(`SysML-v2-Release` tag `2026-05`), and every known deviation.

## Identity, ownership, refs

- Every element has a UUID `element_id`, matching the API JSON `@id`.
- Cross-references are `Ref` objects (UUID wrappers) resolved through the
  model, never direct Python references, so any element serializes alone.
- Ownership lives in the `Model` container (owner/owned maps), not on
  elements.
- `Model.assign_stable_ids()` rewrites ids as UUIDv5 hashes of qualified
  names, so generated interchange files diff cleanly under version control.
  Run it before committing generated models.

## Values with units and provenance

`AttributeValue` holds a literal plus optional `unit` (text, e.g. `"dBW"`),
`source`, and `confidence`. Units stay text in the model for round-trip
fidelity; `sysml2kit.units` (pint) checks them during validation and offers
conversion helpers.

## Two output formats, one lossless

- **JSON interchange** (`sysml2kit.interchange`) is the lossless format and
  what the Systems Modeling API speaks.
- **Textual notation** (`sysml2kit.text`) is deterministic and parseable, but
  relationship kinds without a standalone textual statement (verify, derive)
  emit as marked dependencies. Round-tripping text preserves structure;
  round-tripping JSON preserves everything.

## Spec churn policy

The `@type` vocabulary lives in one module
(`sysml2kit/interchange/typemap.py`). The spec pin moves at most quarterly,
in a minor release, noted in the changelog.

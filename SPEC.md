# sysml2kit specification notes

## Reference spec release

This package targets the OMG SysML v2 standard as published in the
`Systems-Modeling/SysML-v2-Release` repository, tag **`2026-05`**.

Policy: the pin moves at most quarterly, in a minor release, with the change
noted in the changelog. `src/sysml2kit/interchange/typemap.py` is the single
module coupled to the spec's `@type` vocabulary; spec bumps start there.

## The pragmatic profile

sysml2kit does not implement the full KerML/SysML v2 abstract syntax
(~270 metaclasses). It implements a documented subset — the *pragmatic
profile* — chosen to cover requirements-driven architecture work:

| Category | Elements |
|---|---|
| Base | `Element` (abstract), `Relationship` (abstract), `OpaqueElement` |
| Structure | `Package`, `PartDefinition`, `PartUsage`, `PortDefinition`, `PortUsage`, `InterfaceDefinition`, `ConnectionUsage` |
| Values | `AttributeDefinition`, `AttributeUsage` |
| Requirements | `RequirementDefinition`, `RequirementUsage`, `ConstraintUsage` |
| Analysis | `AnalysisCaseDefinition`, `AnalysisCaseUsage` |
| Traceability | `SatisfyRelationship`, `VerifyRelationship`, `DeriveRelationship`, `AllocateRelationship` |
| Annotation | `MetadataDefinition`, `MetadataUsage` |

Everything else round-trips through `OpaqueElement`: on JSON import, an
unrecognized `@type` keeps its raw record and ownership links verbatim, and
re-exports unchanged. Reading a model with sysml2kit and writing it back does
not drop elements the profile lacks classes for.

## Known deviations from the abstract syntax

- **Satisfy/verify/derive/allocate are reified relationship elements.** The
  spec models several of these as membership/annotation forms; sysml2kit
  represents each as a first-class `Relationship` with `source`/`target`
  refs. The JSON writer emits the corresponding standard `@type` names.
- **Feature typing is a field, not a relationship element.** A usage carries
  `definition: Ref | None` instead of an owned `FeatureTyping` element.
- **Multiplicity is opaque text** (`"[1..4]"`), not a modeled expression.
- **Constraint expressions are opaque strings** in v0.1; no expression tree.
- **Units are strings on `AttributeValue`** (e.g. `"dBW"`), checked against
  pint on validation, not references into the ISQ/SI model libraries. The
  textual writer emits them in `[...]` value annotations.
- **Documentation is a field** (`Element.doc`), not an owned `Documentation`
  element; the writer emits `doc /* ... */` bodies.

## Text parse fidelity (sysmlpy backend, 0.36.x)

The backend parses via ``sysmlpy.load_grammar_antlr`` and walks the raw
ANTLR dict (the wrapper-object loader rebuilds usage bodies lossily and is
not used). What survives a text round trip:

| Round-trips | Lost upstream (sysmlpy visitor discards it) |
|---|---|
| names, short names | `dependency A to B;` statements (how the writer emits verify/derive) |
| docs (package/part/requirement scope) | `allocate X to Y;` endpoints |
| feature typing, incl. cross-package | `connect a.pa to b.pb;` endpoints |
| multiplicity | `verification` case usages (dropped entirely) |
| attribute values with units | value provenance (`source`/`confidence` have no textual slot) |
| requirement subject and text | |
| satisfy (package level and inside part bodies) | |

Consequence: **satisfy traceability survives text; verify/derive/allocate
require the JSON interchange.** The losses are pinned by tests in
`tests/test_backend_fidelity.py` so an upstream sysmlpy fix surfaces as a
test failure.

## Identity and ownership

- Every element has a UUID `element_id`, mapping to the API JSON `@id`.
- Cross-references are `Ref` objects (UUID wrappers), never direct Python
  object references, so any element serializes independently.
- Ownership is kept in the `Model` container (owner/owned maps), not on
  elements, mirroring the API's `owningRelatedElement` records.
- `Model.assign_stable_ids()` rewrites ids as UUIDv5 hashes of qualified
  names so generated interchange files diff cleanly under version control.

## Provenance on values

`AttributeValue` carries optional `source` and `confidence` fields, following
the `Assumption` pattern from `spacedc-mdao`: a number in a model should say
where it came from. These fields serialize into the JSON interchange as
metadata and are omitted from the textual notation (which has no standard slot
for them).

# sysml2kit specification notes

## Reference spec release

This package targets the OMG SysML v2 standard as published in the
`Systems-Modeling/SysML-v2-Release` repository, tag **`2026-05`** (still the
newest release tag as of 2026-08-21).

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
not used). The backend also applies guarded runtime patches to sysmlpy's visitor
(``backends/_sysmlpy_patches.py``; upstream: mycr0ft/sysmlpy #6 and #7 plus
the metadata-body issue filed with them). Patches activate only for sysmlpy
0.3x with the expected visitor surface; otherwise the pre-patch losses
apply and their tests document them.

| Round-trips (with patches active) | Still lost |
|---|---|
| names, short names | unnamed `dependency A to B;` statements (the writer emits named `verify_N`/`derive_N` dependencies, which reify) |
| docs (package/part/requirement scope) | `connect a.pa to b.pb;` endpoints |
| feature typing, incl. cross-package | `verification` case usages (dropped entirely) |
| multiplicity | metadata inside definition/case bodies (hence the package-level placement convention below) |
| attribute values with units | value provenance (`source`/`confidence` have no textual slot) |
| requirement subject and text | |
| satisfy, verify, derive, allocate | |
| package-level metadata with scalar values (verificationBinding included) | |

Verify/derive encode as **named dependencies**: ``dependency verify_1 from
ana to R1;`` — the ``verify_``/``derive_`` name prefix is the round-trip
convention. Metadata annotations are placed at package level (the ``about``
reference carries the attachment); ``builder.metadata`` defaults to this.
Endpoint resolution prefers candidates under the same root package, so
multi-package files with repeated short names resolve correctly.

Consequence: **a `.sysml` file is a complete verification artifact** —
`sysml2kit verify` on text produces the same verdicts as on interchange
JSON. Remaining losses are pinned by tests in
`tests/test_backend_fidelity.py`.

## Identity and ownership

- Every element has a UUID `element_id`, mapping to the API JSON `@id`.
- Cross-references are `Ref` objects (UUID wrappers), never direct Python
  object references, so any element serializes independently.
- Ownership is kept in the `Model` container (owner/owned maps), not on
  elements, mirroring the API's `owningRelatedElement` records.
- `Model.assign_stable_ids()` rewrites ids as UUIDv5 hashes of qualified
  names so generated interchange files diff cleanly under version control.

## Verification binding convention

A ``MetadataUsage`` annotating an ``AnalysisCaseUsage`` binds that
analysis to an executable engine when it is recognizable as a
``verificationBinding`` in either of two forms:

- the usage itself is named ``verificationBinding``
  (``metadata verificationBinding about study {...}``), or
- the usage is a *named* usage typed by a
  ``metadata def verificationBinding``
  (``metadata analyticBinding : verificationBinding about study {...}``).

The typed form is required for a fidelity ladder: sibling usages must
carry distinct names for stable-id hashing, so they share the annotation
kind through the definition instead of the name. Values (flat scalars,
per the metadata model):

| key | type | meaning |
|---|---|---|
| ``engine`` | str, required | registry name, e.g. ``"phased-array-systems"`` |
| ``configRef`` | str, optional | ``.yaml``/``.yml``/``.json`` payload file next to the model file (resolved relative to its directory, containment-checked; no ``..``) |
| ``payload.<dotted>`` | scalar, optional | override deep-merged over the loaded config; dotted keys expand to nested dicts |
| ``fidelity`` | str, optional | rung label; sibling bindings on one analysis form a fidelity ladder (labels must be distinct, rule S2K010) |
| ``costSeconds`` | number, optional | declared wall-clock estimate; orders the ladder and gates the escalate policy's budget |

Engines resolve **by name** against a registry populated from the
``sysml2kit.engines`` entry-point group and explicit caller registration.
Model text never names importable code paths — models are data. The runner
does not interpret payload contents; each engine owns its payload schema
(engines needing a config plus scalar arguments define reserved top-level
keys such as ``config``/``args``).

Results written back by ``sysml2kit.verify.apply_results`` are attributes on
the analysis (``source`` starts with ``sysml2kit.verify``) and a
``verificationVerdict`` metadata on each requirement; both replace prior
same-named results, so reruns do not accumulate.

Bindings round-trip through interchange JSON and, at package level, through
the textual notation (see the fidelity table above).

## Provenance on values

`AttributeValue` carries optional `source` and `confidence` fields, following
the `Assumption` pattern from `spacedc-mdao`: a number in a model should say
where it came from. These fields serialize into the JSON interchange as
metadata and are omitted from the textual notation (which has no standard slot
for them).

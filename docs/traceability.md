# Traceability

The queries in `sysml2kit.query` answer the questions a requirements-driven
workflow actually asks:

| Question | Call |
|---|---|
| What satisfies this requirement? | `satisfied_by(model, req)` |
| What verifies it? | `verified_by(model, req)` |
| What does it derive from? | `derived_from(model, req)` |
| Which requirements have no satisfier? | `unsatisfied_requirements(model)` |
| Which have no verifier? | `unverified_requirements(model)` |
| What is allocated where? | `allocation_table(model)` |
| The whole grid at once? | `trace_matrix(model).render()` |

The four relationship kinds are first-class elements
(`SatisfyRelationship`, `VerifyRelationship`, `DeriveRelationship`,
`AllocateRelationship`) created through the builder:

```python
builder.satisfy(model, source=battery, target=mass_req)
builder.verify(model, source=range_analysis, target=range_req)
builder.derive(model, source=mass_req, target=range_req)
builder.allocate(model, source=range_req, target=battery)
```

## Handing requirements to an engine: the metricKey convention

A requirement usage that owns attributes `metricKey` (string), `threshold`
(number with unit), `op` (`>=`, `<=`, `==`, `>`, `<`), and optionally
`severity` (`must`/`should`/`nice`) is machine-checkable.
`sysml2kit.interop.extract_requirements` turns each into a `RequirementSpec`
carrying the threshold in both operator form (`op` + `value`) and bound form
(`minimum`/`maximum`), plus the satisfy/verify trace as qualified names:

```python
from sysml2kit.interop import extract_requirements

for spec in extract_requirements(model):
    print(spec.id, spec.metric_key, spec.op, spec.value, spec.satisfied_by)
```

Both forms are always populated (`>= 40` also sets `minimum=40`), so an
operator-style requirements engine (phased-array-systems) and a bound-style
one (aedl) each need only a small adapter, which lives in those packages.
The metric key names the entry in the engine's metrics dict; the model never
computes anything itself.

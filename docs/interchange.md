# Interchange

## JSON (lossless)

`sysml2kit.interchange` reads and writes the Systems Modeling API
serialization: a flat list of records like

```json
{"@id": "…", "@type": "PartUsage", "declaredName": "battery",
 "owningRelatedElement": {"@id": "…"}, "definition": {"@id": "…"}}
```

- `model_to_json(model)` / `write_json(model, path)` — deterministic output:
  elements sorted by qualified name, keys sorted per record, so committed
  files diff cleanly. Pair with `model.assign_stable_ids()` for generated
  models.
- `model_from_json(records_or_path)` — unknown `@type` records become
  `OpaqueElement` and re-export byte-identically.

`json -> model -> json` is a fixpoint; the property is tested with hypothesis.

## Textual notation (readable, parseable)

`sysml2kit.text.write_model(model)` emits deterministic `.sysml` text:
ownership order, four-space indent, values as `= 52.0 [dBW]`, requirement
statements as `doc` bodies, `satisfy X by Y;` / `allocate X to Y;`
statements. Verify and derive have no standalone textual statement in the
grammar, so they emit as `dependency from A to B; // verify` — the JSON keeps
the precise kind.

Reading text back goes through a [parser backend](backends.md).

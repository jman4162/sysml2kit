# Command line

`sysml2kit` accepts `.json` interchange files everywhere; `.sysml` inputs
need the parse extra (`pip install sysml2kit[parse]`).

```bash
sysml2kit show model.json                 # element tree + counts
sysml2kit show model.json --traceability  # + requirement-to-part matrix
sysml2kit validate a.json b.sysml         # exit 1 on error-severity issues
sysml2kit diff old.json new.json          # exit 1 when models differ
sysml2kit diff old.json new.json --by-name  # match by qualified name, not id
sysml2kit export model.sysml --to json -o model.json
sysml2kit export model.json --to sysml
sysml2kit export model.json --to json --stable-ids  # UUIDv5 ids for committing
sysml2kit version
```

Exit codes: `validate` returns 1 when any error-severity issue is found;
`diff` returns 1 when the models differ. Both suit CI gates.

# sysml2kit

API-first Python tooling for building, querying, validating, and automating
SysML v2 models.

**Status: pre-alpha.** The 0.0.x releases publish the package skeleton; the
object model, textual writer, traceability queries, validation, diff, and API
client land in 0.1.0. Until then, the
[README](https://github.com/jman4162/sysml2kit#readme) and
[SPEC.md](https://github.com/jman4162/sysml2kit/blob/main/SPEC.md) describe
the design: a documented subset of SysML v2 (the "pragmatic profile") as
pydantic models, a deterministic `.sysml` writer, Systems Modeling API JSON
interchange, and parsing delegated to a pluggable backend.

```bash
pip install sysml2kit
```

Reference spec release: OMG `SysML-v2-Release` tag `2026-05`.

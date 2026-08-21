# Parser backends

sysml2kit does not implement the SysML v2 grammar. Reading textual notation
goes through a `ParserBackend` (see `sysml2kit.backends.protocol`):

```python
from sysml2kit.backends import get_backend

backend = get_backend("sysmlpy")
model = backend.parse(text)
model = backend.parse_files([path_a, path_b])
```

## The sysmlpy backend

`pip install sysml2kit[parse]` installs
[sysmlpy](https://github.com/mycr0ft/sysmlpy) (MIT, ANTLR4-based). The
backend parses with `sysmlpy.load_grammar_antlr` and walks the raw ANTLR
dict — sysmlpy's own wrapper loader rebuilds usage bodies lossily, so the
wrappers are not used.

Fidelity: names, short names, docs, feature typing (including
cross-package), multiplicity, attribute values with units, requirement
subjects, and satisfy statements survive a text parse. What cannot
round-trip is what sysmlpy's visitor discards before we see it: `dependency`
statements (how the writer emits verify/derive), `allocate` and `connect`
endpoints, and `verification` cases (filed upstream as sysmlpy #4 and #5).
The fidelity table lives in SPEC.md and is pinned by
`tests/test_backend_fidelity.py`. Use JSON interchange when you need the
full traceability graph.

The dependency is capped (`sysmlpy>=0.36.2,<0.37`) because it has a single
maintainer; bumps are deliberate, after reading the release notes.

## Conformance oracle

A scheduled workflow (`conformance.yml`) downloads the EPL-2.0 OMG pilot
implementation at run time (never vendored) and checks it accepts every
`.sysml` file our writer emits. See `tools/conformance/run_oracle.py`.

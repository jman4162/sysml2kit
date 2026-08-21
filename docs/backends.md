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
adapter maps its parse tree into the pragmatic profile; constructs the
profile lacks come back as `OpaqueElement` with a logged warning.

Fidelity: sysmlpy 0.36 does not surface typing, multiplicity, or attribute
values on its wrapper objects, so those fields are empty after a parse.
Names, kinds, docs, and ownership round-trip; the writer-emit → parse → 
compare test in CI pins exactly that contract. Use JSON interchange when you
need full fidelity.

The dependency is capped (`sysmlpy>=0.36.2,<0.37`) because it has a single
maintainer; bumps are deliberate, after reading the release notes.

## Conformance oracle

A scheduled workflow (`conformance.yml`) downloads the EPL-2.0 OMG pilot
implementation at run time (never vendored) and checks it accepts every
`.sysml` file our writer emits. See `tools/conformance/run_oracle.py`.

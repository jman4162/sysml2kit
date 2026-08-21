# The RF library

sysml2kit stays domain-general. Antenna/RF vocabulary lives in
[sysml2kit-rf-library](https://github.com/jman4162/sysml2kit-rf-library):

```bash
pip install sysml2kit-rf-library
```

```python
from sysml2kit_rf_library import load_model
from sysml2kit.interop import extract_requirements
from sysml2kit.query import trace_matrix

model = load_model("satcom-terminal-t3001")
print(trace_matrix(model).render())
for spec in extract_requirements(model):
    print(spec.id, spec.metric_key, spec.op, spec.value, spec.units)
```

It ships four library packages (RFVocabulary quantity kinds with units,
RFParts part/port definitions, RFRequirements requirement definitions using
the metricKey convention, RFAnalyses analysis case definitions) plus
two worked examples. **SatcomTerminal28GHz** mirrors the aedl `t3-001`
benchmark: eight machine-checkable requirements, each satisfied by a part
and verified by an analysis. **SatcomTerminalPAS** is executable: its
`pasStudy` analysis carries a `verificationBinding` for the
`phased-array-systems` engine, so `sysml2kit verify` runs a real study and
all five requirements pass with margin (see
[verification](verification.md)).

The library demonstrates the intended division of labor: domain vocabulary
as SysML v2 model content, generic mechanics in the kit, physics engines
downstream.

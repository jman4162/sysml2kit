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
**SatcomTerminal28GHz** — a worked example mirroring the aedl `t3-001`
benchmark: a 28 GHz LEO uplink phased-array terminal with eight
machine-checkable requirements (worst-case link margin, sidelobe level,
independent link crosscheck, clear-sky and gain agreement, prime-power and
unit-cost ceilings, grating-lobe margin), each satisfied by a part and
verified by an analysis.

The library demonstrates the intended division of labor: domain vocabulary
as SysML v2 model content, generic mechanics in the kit, physics engines
downstream.

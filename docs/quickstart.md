# Quickstart

Build a model, run the traceability queries, and emit both output formats.

```python
from sysml2kit import Model, builder
from sysml2kit.query import trace_matrix, unverified_requirements
from sysml2kit.text import write_model
from sysml2kit.interchange import write_json
from sysml2kit.validation import validate

model = Model()
pkg = builder.pkg(model, "Vehicle")
battery = builder.part(model, "battery", owner=pkg)
range_req = builder.req(
    model, "REQ-001", "Range", owner=pkg,
    text="The vehicle shall travel at least 400 km on one charge.",
)
builder.satisfy(model, source=battery, target=range_req)

print(unverified_requirements(model))   # [REQ-001] - nothing verifies it yet
print(trace_matrix(model).render())     # requirement-by-part grid
for issue in validate(model):
    print(issue.rule_id, issue.severity, issue.message)

print(write_model(model))               # SysML v2 textual notation
write_json(model, "vehicle.json")       # Systems Modeling API interchange
```

The same operations from the command line:

```bash
sysml2kit show vehicle.json --traceability
sysml2kit validate vehicle.json
sysml2kit export vehicle.json --to sysml
```

Reading `.sysml` text back requires the parse extra:

```python
from sysml2kit.backends import get_backend

model = get_backend("sysmlpy").parse(open("vehicle.sysml").read())
```

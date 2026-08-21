# Verification execution

`sysml2kit.verify` closes the loop the traceability queries only describe:
it runs the analyses a model's verify links point at and checks each
requirement against real metrics.

## The binding convention

An analysis case becomes executable when it carries a `verificationBinding`
metadata (see SPEC.md for the normative statement):

```python
from sysml2kit.model import builder

analysis = builder.analysis(model, "pasStudy", owner=pkg, subject=terminal)
builder.verify(model, source=analysis, target=link_margin_req, owner=pkg)
builder.metadata(
    model,
    analysis,
    {"engine": "phased-array-systems", "configRef": "study.yaml"},
    name="verificationBinding",
)
```

- `engine` names an entry in the engine registry — never a code path.
  Models are data; the registry decides what runs.
- `configRef` points at a YAML/JSON payload next to the model file.
- `payload.<dotted>` values override entries in the loaded config
  (`payload.scenario.range_km: 500`).

## Engines

An engine is a callable: payload dict in, flat metrics mapping out.
Packages ship engines through the `sysml2kit.engines` entry-point group:

```toml
[project.entry-points."sysml2kit.engines"]
phased-array-systems = "phased_array_systems.interop.sysml:run_study"
```

Installing such a package makes its engine available by name. The CLI also
accepts operator-supplied engines (`--engine name=module:function`), and
library callers register directly on an `EngineRegistry`.

## Running

```bash
sysml2kit verify model.json --report run.json
sysml2kit verify model.json --write-back -o annotated.json
```

```python
from sysml2kit.verify import run_verification, apply_results

run = run_verification(model, model_path=path)
print(run.passed)
for verdict in run.requirements:
    print(verdict.requirement_id, verdict.status, verdict.margin)
apply_results(model, run)  # record results into the model, idempotent
```

Each requirement verdict carries the metric key, operator, threshold,
actual value, and margin; `passed` is true only when every must-severity
requirement passes and no engine errored. Metrics that are absent or
non-numeric yield `unknown`, which does not pass. Engine exceptions are
captured per analysis, never raised.

Write-back records each checked metric as an attribute on its analysis with
a provenance `source` (`sysml2kit.verify <engine>==<version> <timestamp>`)
and a `verificationVerdict` metadata on each requirement, replacing prior
results so reruns do not accumulate.

## Fidelity ladders and allocation

An analysis may carry several bindings at different fidelities. Two more
reserved metadata keys describe the ladder: `fidelity` (a rung label such
as `analytic` or `pattern`) and `costSeconds` (the declared wall-clock
estimate that orders the rungs):

```python
builder.metadata(
    model,
    analysis,
    {
        "engine": "phased-array-systems",
        "configRef": "study.yaml",
        "fidelity": "analytic",
        "costSeconds": 0.001,
    },
    name="verificationBinding",
)
builder.metadata(
    model,
    analysis,
    {
        "engine": "phased-array-systems-pattern",
        "configRef": "study.yaml",
        "fidelity": "pattern",
        "costSeconds": 1.0,
    },
    name="verificationBinding",
)
```

The runner's `policy` decides which rungs execute. `all` (default) runs
every rung and reports a verdict per rung, with the cross-rung `spread` as
an honest error bar. `cheapest` runs only the lowest-cost rung per
analysis. `escalate` runs the cheapest rungs, ranks must-requirements by
margin thinness (`|margin| / |threshold|`), and spends the remaining
`budget_s` escalating the thinnest to the next rung; those verdicts carry
`escalated_from`. Every run records `seconds_by_fidelity`, so allocation
claims are auditable.

```bash
sysml2kit verify model.json --policy escalate --budget-s 5 --report run.json
```

Validation rule S2K010 rejects two bindings on one analysis that share a
fidelity label and warns when only some sibling bindings declare one.

Over MCP, the `requirements_verify` tool runs the same flow with
entry-point engines only (plus `policy` and `budget_s` parameters),
returning `passed`, must-failures, `seconds_by_fidelity`, and the report
path.

## End to end with the RF library

With `phased-array-systems` and `sysml2kit-rf-library` installed:

```bash
MODEL=$(python -c 'import sysml2kit_rf_library as m; print(m.models_dir())')/interchange/satcom_terminal_pas.json
sysml2kit verify "$MODEL" --report run.json
```

runs a phased-array study and checks link margin, EIRP, sidelobes, prime
power, and cost against the model's thresholds.

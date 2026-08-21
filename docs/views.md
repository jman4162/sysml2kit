# Diagrams

`sysml2kit.views` renders two mermaid views; output is deterministic, so
diagrams diff cleanly and render anywhere mermaid fences do (these docs,
GitHub, Claude artifacts).

```python
from sysml2kit.views import to_mermaid_trace, to_mermaid_tree

print(to_mermaid_trace(model))   # requirements, parts, analyses + edges
print(to_mermaid_tree(model))    # package/part/port ownership
```

```bash
sysml2kit export model.json --to mermaid --diagram trace -o trace.mmd
sysml2kit export model.json --to mermaid --diagram tree
```

The trace view draws requirements as hexagons, analyses as parallelograms,
and parts as rounded boxes, with edge styles per relationship kind: solid
`satisfy`, dotted `verify`/`derive`, thick `allocate`. Only elements that
participate in a relationship appear, so large models stay readable.

Over MCP, the `model_diagram` tool writes the same views to a `.mmd` file.

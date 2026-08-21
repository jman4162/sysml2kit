# MCP server

`pip install "sysml2kit[mcp]"` and run:

```bash
sysml2kit mcp serve                    # stdio (default)
sysml2kit mcp serve --transport http   # streamable HTTP
```

Client config:

```json
{"mcpServers": {"sysml2kit": {"command": "sysml2kit", "args": ["mcp", "serve"]}}}
```

Every tool takes model file paths (`.json` interchange always works;
`.sysml` needs the `parse` extra), returns a JSON dict with a `status` key,
and reports failures as `{"error": ..., "status": "failed"}` instead of
raising. Artifacts are returned as file paths, not payloads.

| Tool | What it does |
|---|---|
| `model_show(path, traceability)` | Element tree, kind counts, optional trace matrix |
| `model_validate(path)` | S2K rule issues with severity counts |
| `model_diff(path_a, path_b, by_name)` | Element-level differences (capped list) |
| `model_export(path, out, to, stable_ids)` | Convert to interchange JSON or `.sysml` |
| `model_diagram(path, out, kind)` | Write a mermaid `.mmd` (trace or tree view) |
| `requirements_trace(path)` | Matrix plus unsatisfied/unverified lists |
| `requirements_extract(path)` | `RequirementSpec` list (the adapter payload) |
| `library_load(name, out)` | Write a packaged rf-library model as JSON |

A typical agent loop: write a `.sysml` file, `model_validate` it, fix issues,
`requirements_trace` to check coverage, `model_export --stable-ids` to commit
the interchange form, `model_diagram` to explain the result.

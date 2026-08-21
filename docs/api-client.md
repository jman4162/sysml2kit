# API client

`sysml2kit.api.SysMLApiClient` is a hand-written httpx client for the OMG
Systems Modeling API and Services endpoints (the REST binding any conformant
model server exposes).

```python
from sysml2kit.api import SysMLApiClient

with SysMLApiClient("https://models.example.com", token="…") as client:
    for project in client.list_projects():
        print(project.id, project.name)
    model = client.list_elements(project_id, commit_id)  # -> sysml2kit Model
    client.push_model(project_id, model, message="update")
```

Covered in v0.1: `list_projects`, `get_project`, `list_branches`,
`list_commits`, `get_commit`, `get_element`, `list_elements` (returns a
`Model` via the interchange reader), `create_project`, and `push_model`
(POSTs a commit whose change set inserts the model's records). Branch
management and merges are not covered yet.

Failures raise `ApiError(status, detail)`. The client sends the bearer token
to whatever base URL you configure; use HTTPS.

## Local live server and the pilot dialect

`docker compose -f docker/compose.yaml up -d` starts the pilot
implementation (sha-pinned image + postgres); `scripts/wait_for_api.sh`
polls until it answers, and `SYSML2KIT_API_URL=http://localhost:9000
pytest -m api` runs the live round-trip suite (a weekly advisory workflow
does the same in CI). The CLI mirrors the client:

```bash
export SYSML2KIT_API_URL=http://localhost:9000
sysml2kit api projects
sysml2kit api push model.json --project demo --create
sysml2kit api pull demo -o pulled.json
```

The pilot speaks the full abstract syntax, so `push_model` adapts records on
the way out and the interchange reader tolerates the differences on the way
back. What survives a server round trip: element kinds, names, short names,
requirement text. What does not (documented degradations — full fidelity
lives in interchange JSON files): ownership (the pilot models it as
OwningMembership elements and ignores our owner key), verify/derive kinds
(pushed as `Dependency`), multiplicity and doc strings (dropped), and
element ids (the server mints its own, so stable-id workflows are
local-file-only).

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

Server compatibility note: the pilot API-Services implementation has JSON
quirks relative to the spec; compatibility is tested best-effort behind the
`api` pytest marker against a local server, not in default CI.

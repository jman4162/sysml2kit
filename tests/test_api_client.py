import httpx
import pytest
import respx

from sysml2kit.api import ApiError, SysMLApiClient
from sysml2kit.interchange import model_to_json
from sysml2kit.model import Model

BASE = "https://sysml.example.test"


@respx.mock
def test_list_projects():
    respx.get(f"{BASE}/projects").mock(
        return_value=httpx.Response(
            200, json=[{"@id": "p1", "name": "Demo"}, {"@id": "p2", "name": "Other"}]
        )
    )
    with SysMLApiClient(BASE) as client:
        projects = client.list_projects()
    assert [p.id for p in projects] == ["p1", "p2"]
    assert projects[0].name == "Demo"


@respx.mock
def test_bearer_token_sent():
    route = respx.get(f"{BASE}/projects").mock(return_value=httpx.Response(200, json=[]))
    with SysMLApiClient(BASE, token="sekrit") as client:
        client.list_projects()
    assert route.calls.last.request.headers["Authorization"] == "Bearer sekrit"


@respx.mock
def test_error_raises_api_error():
    respx.get(f"{BASE}/projects/missing").mock(
        return_value=httpx.Response(404, text="no such project")
    )
    with SysMLApiClient(BASE) as client, pytest.raises(ApiError) as excinfo:
        client.get_project("missing")
    assert excinfo.value.status == 404


@respx.mock
def test_list_elements_builds_model(vehicle: Model):
    records = model_to_json(vehicle)
    respx.get(f"{BASE}/projects/p1/commits/c1/elements").mock(
        return_value=httpx.Response(200, json=records)
    )
    with SysMLApiClient(BASE) as client:
        model = client.list_elements("p1", "c1")
    assert model_to_json(model) == records


@respx.mock
def test_push_model_sends_change_set(vehicle: Model):
    route = respx.post(f"{BASE}/projects/p1/commits").mock(
        return_value=httpx.Response(200, json={"@id": "c9", "description": "push"})
    )
    with SysMLApiClient(BASE) as client:
        commit = client.push_model("p1", vehicle, message="push")
    assert commit.id == "c9"
    import json

    body = json.loads(route.calls.last.request.content)
    assert body["@type"] == "Commit"
    assert len(body["change"]) == len(vehicle.elements)
    assert all(item["@type"] == "DataVersion" for item in body["change"])


@respx.mock
def test_branch_query_parameter(vehicle: Model):
    route = respx.post(f"{BASE}/projects/p1/commits", params={"branchId": "dev"}).mock(
        return_value=httpx.Response(200, json={"@id": "c1"})
    )
    with SysMLApiClient(BASE) as client:
        client.push_model("p1", vehicle, branch="dev")
    assert route.called


@respx.mock
def test_create_project():
    respx.post(f"{BASE}/projects").mock(
        return_value=httpx.Response(200, json={"@id": "p3", "name": "New"})
    )
    with SysMLApiClient(BASE) as client:
        project = client.create_project("New")
    assert project.id == "p3"

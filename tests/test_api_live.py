"""Round-trip tests against a live Systems Modeling API server.

Run the server with ``docker compose -f docker/compose.yaml up -d`` and
``scripts/wait_for_api.sh``, then ``SYSML2KIT_API_URL=http://localhost:9000
pytest -m api tests/test_api_live.py``. Skipped entirely when the env var is
absent, so the default suite never needs a server.

What the pilot preserves (and these tests assert): element identity, kind,
names, short names. What it does not (documented pilot-dialect
degradations): ownership (it models ownership as OwningMembership elements
and ignores our ``owningRelatedElement`` key), verify/derive kinds (pushed
as Dependency), multiplicity (dropped on push). Full fidelity lives in
interchange JSON files, not on the server.
"""

import os
from uuid import uuid4

import pytest

from sysml2kit.api import SysMLApiClient
from sysml2kit.interchange import model_to_json
from sysml2kit.model import Model, OpaqueElement, RequirementUsage

pytestmark = [
    pytest.mark.api,
    pytest.mark.skipif(not os.environ.get("SYSML2KIT_API_URL"), reason="SYSML2KIT_API_URL not set"),
]

#: Keys the push adapter transforms or the server rewrites; excluded from the
#: field-survival check.
DIALECT_KEYS = {
    "owningRelatedElement",  # pilot models ownership as OwningMembership elements
    "text",
    "source",
    "target",
    "definition",  # list-typed there, adapted on push
    "multiplicity",  # opaque text here, Multiplicity elements there; dropped on push
    "doc",
    "objective",
    "subject",
    "imports",
    "unit",
    "expression",
    "values",
    "annotated",
    # profile fields with no direct pilot property; not stored by the server
}


@pytest.fixture
def client():
    with SysMLApiClient(os.environ["SYSML2KIT_API_URL"], timeout=60.0) as c:
        yield c


def identity(model: Model):
    return {
        (type(el).__name__, el.declared_name)
        for el in model.elements.values()
        if not isinstance(el, OpaqueElement) and el.declared_name
    }


def test_round_trip_preserves_elements(client, vehicle: Model):
    project = client.create_project(f"sysml2kit-live-{uuid4().hex[:8]}")
    commit = client.push_model(project.id, vehicle, message="live round trip")
    assert commit.id

    commits = client.list_commits(project.id)
    assert any(c.id == commit.id for c in commits)

    pulled = client.list_elements(project.id, commit.id)
    assert len(pulled.elements) >= len(vehicle.elements)
    # every named non-relationship element survives with its kind and name
    missing = identity(vehicle) - identity(pulled)
    assert not {m for m in missing if "Relationship" not in m[0]}, missing


def test_requirement_text_and_short_name_survive(client, vehicle: Model):
    project = client.create_project(f"sysml2kit-live-{uuid4().hex[:8]}")
    commit = client.push_model(project.id, vehicle)
    pulled = client.list_elements(project.id, commit.id)
    reqs = {
        el.declared_short_name: el
        for el in pulled.elements.values()
        if isinstance(el, RequirementUsage)
    }
    assert "REQ-001" in reqs
    assert reqs["REQ-001"].text == "The vehicle shall travel at least 400 km on one charge."


def test_pushed_scalar_fields_survive(client, vehicle: Model):
    # The pilot mints its own element ids, so records key by (type, name);
    # stable-id workflows are a local-file concern, not a server one.
    project = client.create_project(f"sysml2kit-live-{uuid4().hex[:8]}")
    commit = client.push_model(project.id, vehicle)
    pulled = client.list_elements(project.id, commit.id)
    pulled_by_name = {
        (r["@type"], r.get("declaredName")): r
        for r in model_to_json(pulled)
        if r.get("declaredName")
    }
    for record in model_to_json(vehicle):
        if not record.get("declaredName") or "Relationship" in type(record).__name__:
            continue
        key_tuple = (record["@type"], record["declaredName"])
        server_record = pulled_by_name.get(key_tuple)
        if server_record is None:
            continue  # relationship kinds remapped to Dependency on push
        for key, value in record.items():
            if value is None or key in DIALECT_KEYS or key.startswith("@"):
                continue
            if isinstance(value, str) and key != "declaredName":
                assert server_record.get(key) == value, (
                    f"{key_tuple}.{key}: pushed {value!r}, server has {server_record.get(key)!r}"
                )


def test_projects_listing_includes_created(client):
    name = f"sysml2kit-live-{uuid4().hex[:8]}"
    created = client.create_project(name)
    assert any(p.id == created.id for p in client.list_projects())

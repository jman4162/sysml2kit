"""A thin, hand-written client for the OMG Systems Modeling API.

Covers the read paths (projects, branches, commits, elements) plus creating
a project and pushing a model as a commit. Hand-written on purpose: the
official generated Python client is LGPL and unmaintained; this one is a few
hundred lines against the REST/JSON binding and returns sysml2kit models.
"""

from __future__ import annotations

import types
from typing import Any, Self

import httpx

from sysml2kit.interchange import model_from_json, model_to_json
from sysml2kit.model.container import Model

from .errors import ApiError
from .models import Branch, Commit, Project


class SysMLApiClient:
    """Synchronous client; use as a context manager to reuse one connection."""

    def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 30.0) -> None:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout)

    # ------------------------------------------------------------- lifecycle
    def close(self) -> None:
        """Close the underlying connection pool."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------- plumbing
    def _get(self, path: str) -> Any:
        response = self._client.get(path)
        if response.status_code >= 400:
            raise ApiError(response.status_code, response.text)
        return response.json()

    def _post(self, path: str, payload: Any) -> Any:
        response = self._client.post(path, json=payload)
        if response.status_code >= 400:
            raise ApiError(response.status_code, response.text)
        return response.json()

    # ---------------------------------------------------------------- reads
    def list_projects(self) -> list[Project]:
        """List projects on the server."""
        return [Project.model_validate(item) for item in self._get("/projects")]

    def get_project(self, project_id: str) -> Project:
        """Fetch one project."""
        return Project.model_validate(self._get(f"/projects/{project_id}"))

    def list_branches(self, project_id: str) -> list[Branch]:
        """List a project's branches."""
        return [
            Branch.model_validate(item) for item in self._get(f"/projects/{project_id}/branches")
        ]

    def list_commits(self, project_id: str) -> list[Commit]:
        """List a project's commits."""
        return [
            Commit.model_validate(item) for item in self._get(f"/projects/{project_id}/commits")
        ]

    def get_commit(self, project_id: str, commit_id: str) -> Commit:
        """Fetch one commit."""
        return Commit.model_validate(self._get(f"/projects/{project_id}/commits/{commit_id}"))

    def get_element(self, project_id: str, commit_id: str, element_id: str) -> dict[str, Any]:
        """Fetch one element's raw interchange record."""
        record = self._get(f"/projects/{project_id}/commits/{commit_id}/elements/{element_id}")
        return dict(record)

    def list_elements(self, project_id: str, commit_id: str) -> Model:
        """Fetch every element at a commit and build a Model from them."""
        records = self._get(f"/projects/{project_id}/commits/{commit_id}/elements")
        return model_from_json(records)

    # --------------------------------------------------------------- writes
    def create_project(self, name: str, *, description: str | None = None) -> Project:
        """Create a project."""
        payload: dict[str, Any] = {"@type": "Project", "name": name}
        if description:
            payload["description"] = description
        return Project.model_validate(self._post("/projects", payload))

    @staticmethod
    def _to_server_record(record: dict[str, Any]) -> dict[str, Any]:
        """Adapt one interchange record to the pilot server's dialect.

        The abstract syntax types relationship ``source``/``target`` as lists
        of related elements; sysml2kit's records carry a single ``{"@id"}``
        (a documented profile simplification). Wrap them on the way out; the
        interchange reader unwraps single-element lists on the way back.
        """
        adapted = dict(record)
        for key in ("source", "target", "definition"):
            value = adapted.get(key)
            if isinstance(value, dict) and set(value) == {"@id"}:
                adapted[key] = [value]
        # Profile simplifications with no server-side shape are dropped on
        # push (multiplicity is opaque text here, a Multiplicity element
        # there). Fidelity lives in interchange JSON files, not the server.
        adapted.pop("multiplicity", None)
        # RequirementUsage/RequirementDefinition `text` is List<String> there.
        if isinstance(adapted.get("text"), str):
            adapted["text"] = [adapted["text"]]
        # The pilot's type vocabulary has no DeriveRequirementUsage or
        # VerifyRequirementUsage; those push as Dependency (client/supplier),
        # losing the kind distinction on pull — same degradation class as the
        # textual notation. Full fidelity lives in interchange JSON files.
        if adapted.get("@type") in ("DeriveRequirementUsage", "VerifyRequirementUsage"):
            adapted["@type"] = "Dependency"
            adapted["client"] = adapted.pop("source", None) or []
            adapted["supplier"] = adapted.pop("target", None) or []
        return adapted

    def push_model(
        self,
        project_id: str,
        model: Model,
        *,
        branch: str | None = None,
        message: str | None = None,
    ) -> Commit:
        """Create a commit whose change set inserts every element of the model."""
        change = [
            {"@type": "DataVersion", "payload": self._to_server_record(record)}
            for record in model_to_json(model)
        ]
        payload: dict[str, Any] = {"@type": "Commit", "change": change}
        if message:
            payload["description"] = message
        path = f"/projects/{project_id}/commits"
        if branch:
            path += f"?branchId={branch}"
        return Commit.model_validate(self._post(path, payload))

    def head_commit(self, project_id: str) -> Commit:
        """Return the newest commit of a project; raises ApiError when empty."""
        commits = self.list_commits(project_id)
        if not commits:
            raise ApiError(404, f"project {project_id} has no commits")
        return commits[-1]

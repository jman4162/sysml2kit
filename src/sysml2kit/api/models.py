"""Resource models for the Systems Modeling API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Project(BaseModel):
    """A model repository project."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="@id")
    name: str | None = None
    description: str | None = None


class Branch(BaseModel):
    """A branch within a project."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="@id")
    name: str | None = None
    head: str | None = None

    @field_validator("head", mode="before")
    @classmethod
    def _head_ref_to_id(cls, value: object) -> object:
        # The pilot sends head as an identified ref: {"@id": "..."}.
        if isinstance(value, dict):
            return value.get("@id")
        return value


class Commit(BaseModel):
    """A commit within a project."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="@id")
    description: str | None = None
    created: str | None = None
    owning_project: str | None = None

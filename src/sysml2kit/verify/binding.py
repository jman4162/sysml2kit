"""The verification binding convention.

A ``MetadataUsage`` named ``verificationBinding`` annotating an
``AnalysisCaseUsage`` binds that analysis to an engine:

- ``engine`` (required): a registry name, e.g. ``"phased-array-systems"``.
- ``configRef`` (optional): a ``.yaml``/``.yml``/``.json`` payload file,
  resolved relative to the model file's directory and containment-checked —
  configs live next to the model.
- ``payload.<dotted.path>`` (optional): scalar overrides deep-merged over the
  loaded config; dotted keys expand to nested dicts.

The runner never interprets payload contents; each engine owns its payload
schema. SPEC.md carries the normative statement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from sysml2kit.model.analysis import AnalysisCaseUsage
from sysml2kit.model.container import Model
from sysml2kit.model.metadata import MetadataUsage
from sysml2kit.workspace import validate_path_within

BINDING_NAME = "verificationBinding"
_PAYLOAD_PREFIX = "payload."


def is_binding(model: Model, element: MetadataUsage) -> bool:
    """Whether this metadata usage is a verificationBinding.

    Either the usage itself is named ``verificationBinding`` or it is a
    named usage typed by a ``metadata def verificationBinding`` — the
    typed form is what lets several sibling bindings (a fidelity ladder)
    coexist with distinct names.
    """
    if element.declared_name == BINDING_NAME:
        return True
    if element.definition is not None and element.definition.target in model.elements:
        return model.resolve(element.definition).declared_name == BINDING_NAME
    return False


class BindingError(ValueError):
    """A verificationBinding metadata is malformed or unresolvable."""


class VerificationBinding(BaseModel):
    """One analysis-to-engine binding extracted from a model."""

    analysis_id: str
    analysis: str
    engine: str
    config_ref: str | None = None
    overrides: dict[str, float | int | str | bool] = {}
    #: Rung label from the reserved ``fidelity`` metadata key.
    fidelity: str | None = None
    #: Declared wall-clock estimate from the reserved ``costSeconds`` key.
    cost_s: float | None = None

    @property
    def key(self) -> str:
        """Stable identity for one rung of one analysis."""
        return f"{self.analysis}#{self.fidelity or self.engine}"


def extract_bindings(model: Model) -> list[VerificationBinding]:
    """Return every verificationBinding in the model, in ownership order."""
    bindings: list[VerificationBinding] = []
    for element in model.iter_elements(kind=MetadataUsage):
        assert isinstance(element, MetadataUsage)
        if not is_binding(model, element):
            continue
        if element.annotated is None:
            raise BindingError(f"binding {element.element_id} annotates nothing")
        try:
            analysis = model.resolve(element.annotated)
        except KeyError as exc:
            raise BindingError(f"binding {element.element_id} annotates a missing element") from exc
        if not isinstance(analysis, AnalysisCaseUsage):
            raise BindingError(
                f"binding {element.element_id} annotates {type(analysis).__name__}, "
                "expected an analysis case usage"
            )
        engine = element.values.get("engine")
        if not isinstance(engine, str) or not engine:
            raise BindingError(f"binding on '{model.qualified_name(analysis)}' names no engine")
        config_ref = element.values.get("configRef")
        fidelity = element.values.get("fidelity")
        cost = element.values.get("costSeconds")
        overrides = {
            key[len(_PAYLOAD_PREFIX) :]: value
            for key, value in element.values.items()
            if key.startswith(_PAYLOAD_PREFIX)
        }
        bindings.append(
            VerificationBinding(
                analysis_id=str(analysis.element_id),
                analysis=model.qualified_name(analysis),
                engine=engine,
                config_ref=str(config_ref) if config_ref is not None else None,
                overrides=overrides,
                fidelity=str(fidelity) if fidelity is not None else None,
                cost_s=float(cost) if isinstance(cost, int | float) else None,
            )
        )
    return bindings


def build_payload(binding: VerificationBinding, base_dir: Path) -> dict[str, Any]:
    """Load the binding's config file and merge its dotted-key overrides."""
    payload: dict[str, Any] = {}
    if binding.config_ref:
        path = validate_path_within(base_dir / binding.config_ref, base_dir)
        if path.suffix == ".json":
            payload = json.loads(path.read_text())
        elif path.suffix in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError as exc:
                raise ImportError(
                    "YAML configs need the 'verify' extra: pip install sysml2kit[verify]"
                ) from exc
            payload = yaml.safe_load(path.read_text()) or {}
        else:
            raise BindingError(f"configRef {binding.config_ref!r}: expected .json/.yaml/.yml")
        if not isinstance(payload, dict):
            raise BindingError(f"configRef {binding.config_ref!r} did not contain a mapping")
    for dotted, value in binding.overrides.items():
        _set_dotted(payload, dotted, value)
    return payload


def _set_dotted(target: dict[str, Any], dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    node = target
    for key in keys[:-1]:
        nxt = node.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            node[key] = nxt
        node = nxt
    node[keys[-1]] = value

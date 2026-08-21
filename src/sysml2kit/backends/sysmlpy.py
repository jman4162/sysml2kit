"""The sysmlpy parse backend (``pip install sysml2kit[parse]``).

Parses with ``sysmlpy.load_grammar_antlr`` and walks the raw ANTLR dict it
returns, rather than sysmlpy's wrapper objects: the wrapper loader rebuilds
usage bodies lossily (dropping satisfy statements, docs, and ports inside
parts), while the raw dict keeps what the visitor captured — names, short
names, docs, feature typing, multiplicity, attribute values with units,
requirement subjects, and satisfy statements.

Constructs the visitor itself discards cannot round-trip and are logged once
per parse: ``dependency`` statements (how the writer emits verify/derive),
``allocate``/``connect`` endpoints, and ``verification`` cases. SPEC.md
carries the full fidelity table.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from sysml2kit.model.analysis import AnalysisCaseDefinition, AnalysisCaseUsage
from sysml2kit.model.base import Element, Ref
from sysml2kit.model.container import Model
from sysml2kit.model.relations import SatisfyRelationship
from sysml2kit.model.requirements import (
    ConstraintUsage,
    RequirementDefinition,
    RequirementUsage,
)
from sysml2kit.model.structure import (
    AttributeDefinition,
    AttributeUsage,
    ConnectionUsage,
    InterfaceDefinition,
    Package,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
)
from sysml2kit.model.values import AttributeValue

logger = logging.getLogger(__name__)

#: Raw-dict node type -> profile class.
_NODE_MAP: dict[str, type[Element]] = {
    "Package": Package,
    "PartDefinition": PartDefinition,
    "PartUsage": PartUsage,
    "PortDefinition": PortDefinition,
    "PortUsage": PortUsage,
    "InterfaceDefinition": InterfaceDefinition,
    "AttributeDefinition": AttributeDefinition,
    "AttributeUsage": AttributeUsage,
    "RequirementDefinition": RequirementDefinition,
    "RequirementUsage": RequirementUsage,
    "ConstraintUsage": ConstraintUsage,
    "AnalysisCaseDefinition": AnalysisCaseDefinition,
    "AnalysisCaseUsage": AnalysisCaseUsage,
    "ConnectionUsage": ConnectionUsage,
}

#: Keys never descended when extracting declaration-level facts.
_BODY_KEYS = frozenset({"body", "completion"})


def _require_sysmlpy() -> Any:
    try:
        import sysmlpy
    except ImportError as exc:  # pragma: no cover - exercised via the error message test
        raise ImportError("parsing needs the 'parse' extra: pip install sysml2kit[parse]") from exc
    return sysmlpy


# ------------------------------------------------------------- dict walkers
def _iter_nodes(
    node: Any, name: str, *, skip_keys: frozenset[str] = frozenset()
) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        if node.get("name") == name:
            yield node
        for key, value in node.items():
            if key == "name" or key in skip_keys:
                continue
            yield from _iter_nodes(value, name, skip_keys=skip_keys)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_nodes(item, name, skip_keys=skip_keys)


def _first(
    node: Any, name: str, *, skip_keys: frozenset[str] = frozenset()
) -> dict[str, Any] | None:
    return next(_iter_nodes(node, name, skip_keys=skip_keys), None)


def _identification(node: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (declared_name, declared_short_name) from the declaration scope."""
    ident = _first(node, "Identification", skip_keys=_BODY_KEYS)
    if ident is None:
        return None, None
    short = ident.get("declaredShortName")
    if isinstance(short, str):
        short = short.strip("<>").strip().strip("'")
    return ident.get("declaredName"), short


def _typing_names(node: dict[str, Any]) -> list[str] | None:
    """Return the qualified-name segments of the first feature typing, if any."""
    typing = _first(node, "FeatureTyping", skip_keys=_BODY_KEYS)
    if typing is None:
        return None
    qualified = _first(typing, "QualifiedName")
    names = qualified.get("names") if qualified else None
    return list(names) if names else None


def _multiplicity_text(node: dict[str, Any]) -> str | None:
    """Reconstruct multiplicity text like ``[2]`` or ``[1..*]``."""
    part = _first(node, "MultiplicityPart", skip_keys=_BODY_KEYS)
    if part is None:
        return None
    bounds: list[str] = []
    for member in _iter_nodes(part, "MultiplicityExpressionMember"):
        for literal_kind in ("LiteralInteger", "LiteralReal", "LiteralInfinity"):
            literal = _first(member, literal_kind)
            if literal is not None:
                bounds.append(str(literal.get("value")))
                break
    if not bounds:
        return None
    return f"[{bounds[0]}]" if len(bounds) == 1 else f"[{bounds[0]}..{bounds[1]}]"


def _attribute_value(node: dict[str, Any]) -> AttributeValue | None:
    """Extract ``= 52.0 [dBW]`` style values from the usage completion."""
    value_part = _first(node, "ValuePart", skip_keys=frozenset({"body"}))
    if value_part is None:
        return None
    primary = _first(value_part, "PrimaryExpression")
    literal: float | int | str | bool | None = None
    unit: str | None = None
    if primary is not None:
        base = primary.get("base")
        for kind, convert in (
            ("LiteralReal", float),
            ("LiteralInteger", int),
            ("LiteralString", lambda s: str(s).strip('"')),
            ("LiteralBoolean", lambda s: str(s).lower() == "true"),
        ):
            found = _first(base, kind)
            if found is not None:
                literal = convert(found.get("value"))  # type: ignore[arg-type]
                break
        if primary.get("operator") == ["["]:
            qualified = _first(primary.get("operand"), "QualifiedName")
            if qualified and qualified.get("names"):
                unit = "::".join(qualified["names"])
    if literal is None:
        # Non-literal expression: keep the raw text so nothing silently vanishes.
        text = _dump_text(value_part)
        if not text:
            return None
        literal = text
    return AttributeValue(value=literal, unit=unit)


def _dump_text(node: Any) -> str:
    """Best-effort source-ish text for an expression subtree."""
    pieces: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            if "value" in item and not isinstance(item["value"], dict | list):
                pieces.append(str(item["value"]))
            for key, value in item.items():
                if key != "name":
                    walk(value)
        elif isinstance(item, list):
            for sub in item:
                walk(sub)

    walk(node)
    return " ".join(dict.fromkeys(pieces))


def _doc_texts(node: dict[str, Any]) -> list[str]:
    """Documentation bodies directly inside this element (not nested elements)."""
    texts = []
    for doc in _iter_nodes_stopping(
        node, "Documentation", stop_names=frozenset(_NODE_MAP), is_root=True
    ):
        body = doc.get("body", "")
        texts.append(re.sub(r"^/\*\s?|\s?\*/$", "", body).strip())
    return texts


def _iter_nodes_stopping(
    node: Any, name: str, *, stop_names: frozenset[str], is_root: bool = False
) -> Iterator[dict[str, Any]]:
    """Like _iter_nodes but does not descend into nested element nodes."""
    if isinstance(node, dict):
        node_name = node.get("name")
        if node_name == name:
            yield node
            return
        if not is_root and isinstance(node_name, str) and node_name in stop_names:
            return
        for key, value in node.items():
            if key != "name":
                yield from _iter_nodes_stopping(value, name, stop_names=stop_names)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_nodes_stopping(item, name, stop_names=stop_names)


def _subject_name(node: dict[str, Any]) -> list[str] | None:
    member = _first(node.get("body"), "SubjectMember")
    if member is None:
        return None
    ident = _first(member, "Identification")
    if ident and ident.get("declaredName"):
        return [ident["declaredName"]]
    return None


def _satisfy_endpoints(node: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return (source path names, target requirement names) for a satisfy node."""
    target = _first(node.get("ors") or node.get("declaration"), "QualifiedName")
    target_names = list(target["names"]) if target and target.get("names") else []
    source_names: list[str] = []
    for qualified in _iter_nodes(node.get("ssm"), "QualifiedName"):
        for name in qualified.get("names") or []:
            # Feature chains arrive as one dotted string ("t.array").
            source_names.extend(name.split("."))
    return source_names, target_names


def _import_texts(node: dict[str, Any]) -> list[str]:
    """Import statements directly inside this package, as ``Name::*`` texts.

    A NamespaceImport is the ``X::*`` form; a MembershipImport (``X::member``)
    keeps its plain qualified name.
    """
    texts = []
    stop = frozenset(_NODE_MAP)
    for kind, suffix in (("NamespaceImport", "::*"), ("MembershipImport", "")):
        for imp in _iter_nodes_stopping(node, kind, stop_names=stop, is_root=True):
            qualified = _first(imp, "QualifiedName")
            if qualified and qualified.get("names"):
                texts.append("::".join(qualified["names"]) + suffix)
    return texts


#: Grammar node names counted by :func:`grammar_signature`; infrastructure
#: wrappers whose names merely end in Usage are excluded.
_SIGNATURE_EXTRA = frozenset(
    {
        "Package",
        "Documentation",
        "NamespaceImport",
        "MembershipImport",
        # Metadata and annotation nodes carry verification bindings; missing
        # them let fmt silently delete bindings before 0.3.1.
        "MetadataFeature",
        "MetadataDefinition",
        "AnnotatingElement",
        "Dependency",
    }
)
_SIGNATURE_EXCLUDE = frozenset({"Usage", "SubjectUsage"})


def grammar_signature(text: str) -> dict[str, int]:
    """Count element-level grammar nodes in the raw parse of ``text``.

    ``fmt`` compares signatures of input and output: a construct the model
    layer cannot represent (a state machine, say) still appears here, so
    dropping it shows up as a count mismatch even though ``diff_models``
    cannot see it.
    """
    sysmlpy = _require_sysmlpy()
    raw = sysmlpy.load_grammar_antlr(text)
    counts: dict[str, int] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            node_name = node.get("name")
            if (
                isinstance(node_name, str)
                and node_name not in _SIGNATURE_EXCLUDE
                and (node_name.endswith(("Usage", "Definition")) or node_name in _SIGNATURE_EXTRA)
            ):
                counts[node_name] = counts.get(node_name, 0) + 1
            for key, value in node.items():
                if key != "name":
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(raw)
    return counts


# ------------------------------------------------------------- the backend
class SysmlpyBackend:
    """Parse SysML v2 text with sysmlpy's ANTLR visitor and map the raw dict."""

    name = "sysmlpy"

    def parse(self, text: str, *, filename: str | None = None) -> Model:
        """Parse one unit of textual notation."""
        sysmlpy = _require_sysmlpy()
        from sysml2kit.backends.protocol import ParseError

        try:
            raw = sysmlpy.load_grammar_antlr(text)
        except sysmlpy.SysMLSyntaxError as exc:
            raise ParseError(str(exc), filename=filename) from exc

        model = Model()
        state = _WalkState()
        self._walk(raw, model, owner=None, state=state)
        _resolve(model, state)
        return model

    def parse_files(self, paths: Sequence[Path]) -> Model:
        """Parse several files into one model (each file's packages become roots)."""
        model = Model()
        state = _WalkState()
        sysmlpy = _require_sysmlpy()
        from sysml2kit.backends.protocol import ParseError

        for path in paths:
            try:
                raw = sysmlpy.load_grammar_antlr(path.read_text())
            except sysmlpy.SysMLSyntaxError as exc:
                raise ParseError(str(exc), filename=str(path)) from exc
            self._walk(raw, model, owner=None, state=state)
        _resolve(model, state)
        return model

    def _walk(self, node: Any, model: Model, owner: Element | None, state: _WalkState) -> None:
        if isinstance(node, list):
            for item in node:
                self._walk(item, model, owner, state)
            return
        if not isinstance(node, dict):
            return
        node_name = node.get("name")

        if node_name == "SatisfyRequirementUsage":
            source, target = _satisfy_endpoints(node)
            if source and target:
                state.satisfies.append((owner, source, target))
            else:
                logger.warning("satisfy statement with unresolvable endpoints kept as-is")
            return

        cls = _NODE_MAP.get(node_name) if isinstance(node_name, str) else None
        if cls is None:
            for key, value in node.items():
                if key != "name":
                    self._walk(value, model, owner, state)
            return

        element = self._build_element(cls, node, model, owner, state)
        body = node.get("body") or (_first(node, "UsageBody", skip_keys=frozenset()) or {})
        self._walk(body, model, element, state)

    def _build_element(
        self,
        cls: type[Element],
        node: dict[str, Any],
        model: Model,
        owner: Element | None,
        state: _WalkState,
    ) -> Element:
        declared, short = _identification(node)
        kwargs: dict[str, Any] = {"declared_name": declared, "declared_short_name": short}

        docs = _doc_texts(node)
        if cls is RequirementUsage:
            if len(docs) >= 2:
                kwargs["doc"], kwargs["text"] = docs[0], docs[1]
            elif docs:
                kwargs["text"] = docs[0]
        elif cls is AnalysisCaseUsage:
            if len(docs) >= 2:
                kwargs["doc"], kwargs["objective"] = docs[0], docs[1]
            elif docs:
                kwargs["objective"] = docs[0]
        elif docs:
            kwargs["doc"] = docs[0]

        if cls is Package:
            kwargs["imports"] = _import_texts(node)
        if cls is PartUsage:
            kwargs["multiplicity"] = _multiplicity_text(node)
        if cls is AttributeUsage:
            kwargs["value"] = _attribute_value(node)

        element = cls(**{k: v for k, v in kwargs.items() if v is not None})
        model.add(element, owner=owner)

        typing = _typing_names(node)
        if typing and cls is not Package:
            state.typings.append((element, typing))
        if cls in (RequirementUsage, AnalysisCaseUsage):
            subject = _subject_name(node)
            if subject:
                state.subjects.append((element, subject))
        return element


class _WalkState:
    def __init__(self) -> None:
        self.typings: list[tuple[Element, list[str]]] = []
        self.subjects: list[tuple[Element, list[str]]] = []
        self.satisfies: list[tuple[Element | None, list[str], list[str]]] = []


def _resolve(model: Model, state: _WalkState) -> None:
    table = {model.qualified_name(eid): eid for eid in model.elements}

    def lookup(names: list[str]) -> Element | None:
        path = "::".join(names)
        if path in table:
            return model.elements[table[path]]
        suffix_matches = [eid for qname, eid in table.items() if qname.endswith("::" + path)]
        if len(suffix_matches) == 1:
            return model.elements[suffix_matches[0]]
        if len(names) == 1:
            name_matches = [el for el in model.elements.values() if el.declared_name == names[0]]
            if len(name_matches) == 1:
                return name_matches[0]
        return None

    for element, names in state.typings:
        target = lookup(names)
        if target is not None and hasattr(element, "definition"):
            element.definition = Ref.to(target)
    for element, names in state.subjects:
        target = lookup(names)
        if target is not None and hasattr(element, "subject"):
            element.subject = Ref.to(target)
    for owner, source_names, target_names in state.satisfies:
        source = lookup(source_names)
        target = lookup(target_names)
        if source is None or target is None:
            logger.warning("unresolved satisfy endpoints: %s -> %s", source_names, target_names)
            continue
        rel = SatisfyRelationship(source=Ref.to(source), target=Ref.to(target))
        model.add(rel, owner=owner)

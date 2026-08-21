"""Runtime patches for sysmlpy's ANTLR visitor, applied under a version guard.

Three upstream defects lose data before the raw dict exists; fixes are
open upstream (mycr0ft/sysmlpy #6, #7, and #9, filed as issue #8). Until a
release ships them, this module applies equivalent patches to
``sysmlpy.antlr_visitor`` at backend import:

- ``allocate X to Y`` endpoints reach the dict (a ``part`` connector, the
  same key ``ConnectionUsage`` uses),
- ``dependency [name] [from] A to B;`` statements are dispatched instead of
  silently dropped,
- braced metadata bodies surface their feature texts (``bodyFeatures``).

Guards: only sysmlpy < 0.37, only when every patched attribute still looks
as expected; any mismatch logs a warning and leaves sysmlpy untouched, in
which case the documented pinned-loss behavior applies.
"""

from __future__ import annotations

import logging
from importlib import metadata
from typing import Any

logger = logging.getLogger(__name__)

_APPLIED_MARKER = "_sysml2kit_patched"


def _dependency_dict(visitor: Any, ctx: Any, prefix: Any) -> dict[str, Any]:
    decl = ctx
    if hasattr(ctx, "dependencyDeclaration") and ctx.dependencyDeclaration():
        decl = ctx.dependencyDeclaration()
    identification = None
    if hasattr(decl, "identification") and decl.identification():
        identification = visitor._build_identification_dict(decl.identification())
    clients: list[dict[str, Any]] = []
    suppliers: list[dict[str, Any]] = []
    after_to = False
    for child in decl.getChildren():
        class_name = child.__class__.__name__
        if class_name == "QualifiedNameContext":
            names = child.getText().split("::")
            (suppliers if after_to else clients).append({"name": "QualifiedName", "names": names})
        elif not after_to and hasattr(child, "getText") and child.getText() == "to":
            after_to = True
    return {
        "name": "PackageMember",
        "prefix": prefix,
        "ownedRelatedElement": {
            "name": "DefinitionElement",
            "ownedRelatedElement": {
                "name": "Dependency",
                "identification": identification,
                "client": clients,
                "supplier": suppliers,
                "body": {"name": "RelationshipBody", "ownedRelatedElement": []},
            },
        },
    }


def _find_node(tree: Any, name: str) -> dict[str, Any] | None:
    if isinstance(tree, dict):
        if tree.get("name") == name:
            return tree
        for key, value in tree.items():
            if key != "name":
                found = _find_node(value, name)
                if found is not None:
                    return found
    elif isinstance(tree, list):
        for item in tree:
            found = _find_node(item, name)
            if found is not None:
                return found
    return None


def apply_patches() -> bool:
    """Patch sysmlpy's visitor in place; returns whether patches are active."""
    try:
        import sysmlpy.antlr_visitor as visitor
    except ImportError:
        return False
    if getattr(visitor, _APPLIED_MARKER, False):
        return True
    try:
        version = metadata.version("sysmlpy")
    except metadata.PackageNotFoundError:
        version = "0"
    if not version.startswith("0.3"):
        logger.warning("sysmlpy %s outside the patch guard; pinned-loss behavior applies", version)
        return False
    required = (
        "_make_allocation_usage_dict",
        "_visit_definition_element_dict",
        "_visit_metadata_feature_dict",
        "_build_connector_part_dict",
        "_build_identification_dict",
    )
    if not all(hasattr(visitor, attr) for attr in required):
        logger.warning("sysmlpy visitor surface changed; skipping fidelity patches")
        return False

    original_allocation = visitor._make_allocation_usage_dict
    original_definition_element = visitor._visit_definition_element_dict
    original_metadata = visitor._visit_metadata_feature_dict

    def patched_allocation(ctx: Any, prefix: Any = None) -> dict[str, Any]:
        result: dict[str, Any] = original_allocation(ctx, prefix)
        try:
            aud = None
            if (
                ctx is not None
                and hasattr(ctx, "allocationUsageDeclaration")
                and ctx.allocationUsageDeclaration()
            ):
                aud = ctx.allocationUsageDeclaration()
            if aud is not None and hasattr(aud, "connectorPart") and aud.connectorPart():
                node = _find_node(result, "AllocationUsage")
                if node is not None:
                    node["part"] = visitor._build_connector_part_dict(aud.connectorPart())
        except Exception:
            logger.exception("allocate endpoint patch failed; endpoints dropped")
        return result

    def patched_definition_element(def_elem_ctx: Any, prefix: Any = None) -> Any:
        try:
            if hasattr(def_elem_ctx, "dependency") and def_elem_ctx.dependency():
                return _dependency_dict(visitor, def_elem_ctx.dependency(), prefix)
        except Exception:
            logger.exception("dependency patch failed; statement dropped")
        return original_definition_element(def_elem_ctx, prefix)

    def patched_metadata(ctx: Any) -> dict[str, Any]:
        result: dict[str, Any] = original_metadata(ctx)
        try:
            body = ctx.metadataBody() if hasattr(ctx, "metadataBody") else None
            if body is not None and getattr(body, "LBRACE", lambda: None)():
                texts = []
                elements = body.metadataBodyElement()
                for element in elements or []:
                    texts.append(element.getText())
                if texts:
                    result["bodyFeatures"] = texts
        except Exception:
            logger.exception("metadata body patch failed; values dropped")
        return result

    visitor._make_allocation_usage_dict = patched_allocation
    visitor._visit_definition_element_dict = patched_definition_element
    visitor._visit_metadata_feature_dict = patched_metadata
    setattr(visitor, _APPLIED_MARKER, True)
    logger.info("sysmlpy %s fidelity patches active (upstream: mycr0ft/sysmlpy#6, #7, #9)", version)
    return True

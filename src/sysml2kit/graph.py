"""NetworkX export (``pip install sysml2kit[graph]``)."""

from __future__ import annotations

from typing import Any

from sysml2kit.model.base import Relationship
from sysml2kit.model.container import Model


def to_networkx(model: Model) -> Any:
    """Build a directed graph: ownership and relationships become edges.

    Nodes are element-id strings with ``kind``/``name`` attributes; edges carry
    ``kind="owns"`` or the relationship class name.
    """
    try:
        import networkx
    except ImportError as exc:
        raise ImportError(
            "graph export needs the 'graph' extra: pip install sysml2kit[graph]"
        ) from exc

    graph = networkx.DiGraph()
    for eid, element in model.elements.items():
        graph.add_node(str(eid), kind=type(element).__name__, name=element.label)
    for child, owner in model.owner.items():
        graph.add_edge(str(owner), str(child), kind="owns")
    for element in model.elements.values():
        if isinstance(element, Relationship):
            graph.add_edge(
                str(element.source.target),
                str(element.target.target),
                kind=type(element).__name__,
            )
    return graph

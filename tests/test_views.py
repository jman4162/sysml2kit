from sysml2kit.model import Model
from sysml2kit.views import to_mermaid_trace, to_mermaid_tree


def test_tree_contains_hierarchy(vehicle: Model, file_regression):
    out = to_mermaid_tree(vehicle)
    assert out.startswith("flowchart TD")
    assert 'Vehicle["Vehicle"]' in out
    assert "Vehicle --> Vehicle__battery" in out
    file_regression.check(out, extension=".tree.mmd")


def test_trace_contains_all_edge_kinds(vehicle: Model, file_regression):
    out = to_mermaid_trace(vehicle)
    assert out.startswith("flowchart LR")
    assert "-- satisfy -->" in out
    assert "-. verify .->" in out
    assert "-. derive .->" in out
    assert "== allocate ==>" in out
    file_regression.check(out, extension=".trace.mmd")


def test_requirement_nodes_use_short_names(vehicle: Model):
    out = to_mermaid_trace(vehicle)
    assert '{{"REQ-001"}}' in out
    assert '{{"REQ-002"}}' in out


def test_deterministic(vehicle: Model):
    assert to_mermaid_trace(vehicle) == to_mermaid_trace(vehicle)
    assert to_mermaid_tree(vehicle) == to_mermaid_tree(vehicle)


def test_empty_model():
    model = Model()
    assert to_mermaid_trace(model) == "flowchart LR\n"
    assert to_mermaid_tree(model) == "flowchart TD\n"

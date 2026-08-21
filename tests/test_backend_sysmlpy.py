import pytest

pytest.importorskip("sysmlpy")

from sysml2kit.backends import get_backend
from sysml2kit.backends.protocol import ParseError, ParserBackend
from sysml2kit.model import Package, PartDefinition, PartUsage, RequirementUsage

pytestmark = pytest.mark.parse

backend = get_backend("sysmlpy")


def test_satisfies_protocol():
    assert isinstance(backend, ParserBackend)
    assert backend.name == "sysmlpy"


def test_parse_basic_structure():
    model = backend.parse(
        """package Demo {
    part def Widget;
    part w1 {
        attribute mass = 2.0 [kg];
    }
    requirement <'R1'> MassLimit;
}"""
    )
    pkg = model.find(name="Demo")
    assert len(pkg) == 1
    assert isinstance(pkg[0], Package)
    assert isinstance(model.find(name="Widget")[0], PartDefinition)
    assert isinstance(model.find(name="w1")[0], PartUsage)
    assert isinstance(model.find(name="MassLimit")[0], RequirementUsage)
    assert model.qualified_name(model.find(name="w1")[0]) == "Demo::w1"


def test_ownership_nesting():
    model = backend.parse("package Outer { part a { attribute x = 1.0; port p; } }")
    a = model.find(name="a")[0]
    child_names = {c.declared_name for c in model.owned_by(a)}
    assert child_names == {"x", "p"}


def test_syntax_error_raises_parse_error():
    with pytest.raises(ParseError, match="Syntax error"):
        backend.parse("package { this is not sysml }", filename="bad.sysml")


def test_unknown_backend_name():
    from sysml2kit.backends import get_backend as gb

    with pytest.raises(KeyError, match="unknown backend"):
        gb("nope")

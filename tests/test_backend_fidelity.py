"""Parse-fidelity tests for the raw-dict sysmlpy backend.

These pin the v0.2 contract: names, short names, docs, feature typing,
multiplicity, attribute values with units, requirement subjects, and satisfy
traceability survive a text parse. Constructs sysmlpy's visitor discards
(dependency statements, allocate/connect endpoints, verification cases) are
pinned as documented losses so an upstream fix shows up as a test failure.
"""

import pytest

pytest.importorskip("sysmlpy")

from sysml2kit.backends import get_backend
from sysml2kit.diff import diff_models
from sysml2kit.model import (
    AttributeUsage,
    Model,
    PartUsage,
    RequirementUsage,
    SatisfyRelationship,
    builder,
)
from sysml2kit.text import write_model

pytestmark = pytest.mark.parse

backend = get_backend("sysmlpy")


def parse(text: str) -> Model:
    return backend.parse(text)


def test_short_name():
    model = parse("package P { requirement <'REQ-001'> Range; }")
    req = model.find(name="Range")[0]
    assert req.declared_short_name == "REQ-001"


def test_cross_package_typing():
    model = parse("package Lib { part def Widget; }\npackage P { part b : Lib::Widget; }")
    b = model.find(name="b")[0]
    assert isinstance(b, PartUsage)
    assert b.definition is not None
    assert model.resolve(b.definition).declared_name == "Widget"


def test_same_package_typing():
    model = parse("package P { part def Amp; part a1 : Amp; }")
    a1 = model.find(name="a1")[0]
    assert isinstance(a1, PartUsage)
    assert a1.definition is not None


@pytest.mark.parametrize(
    ("mult", "expected"), [("[2]", "[2]"), ("[1..*]", "[1..*]"), ("[1..4]", "[1..4]")]
)
def test_multiplicity(mult, expected):
    model = parse(f"package P {{ part motors {mult}; }}")
    motors = model.find(name="motors")[0]
    assert isinstance(motors, PartUsage)
    assert motors.multiplicity == expected


def test_attribute_value_real_with_unit():
    model = parse("package P { part b { attribute cap = 75.5 [kWh]; } }")
    cap = model.find(name="cap")[0]
    assert isinstance(cap, AttributeUsage)
    assert cap.value is not None
    assert cap.value.value == 75.5
    assert cap.value.unit == "kWh"


def test_attribute_value_int_and_string():
    model = parse('package P { attribute n = 4; attribute pol = "RHCP"; }')
    n = model.find(name="n")[0]
    pol = model.find(name="pol")[0]
    assert n.value.value == 4  # type: ignore[union-attr]
    assert pol.value.value == "RHCP"  # type: ignore[union-attr]


def test_requirement_subject_and_text():
    model = parse(
        "package P { part b; requirement <'R1'> A { doc /* the shall text */ subject b; } }"
    )
    req = model.find(name="A")[0]
    assert isinstance(req, RequirementUsage)
    assert req.text == "the shall text"
    assert req.subject is not None
    assert model.resolve(req.subject).declared_name == "b"


def test_docs_at_three_scopes():
    model = parse(
        "package P { doc /* pkg doc */ part b { doc /* part doc */ } "
        "requirement <'R1'> A { doc /* req text */ } }"
    )
    assert model.find(name="P")[0].doc == "pkg doc"
    assert model.find(name="b")[0].doc == "part doc"
    req = model.find(name="A")[0]
    assert isinstance(req, RequirementUsage)
    assert req.text == "req text"


def test_satisfy_at_package_level():
    model = parse("package P { part b; requirement <'R1'> A; satisfy A by b; }")
    rels = model.relationships(kind=SatisfyRelationship)
    assert len(rels) == 1
    assert model.resolve(rels[0].source).declared_name == "b"
    assert model.resolve(rels[0].target).declared_name == "A"


def test_satisfy_inside_part_body():
    # The wrapper-object API drops this; the raw dict keeps it.
    model = parse("package P { requirement <'R1'> A; part amp { satisfy A by amp; } }")
    rels = model.relationships(kind=SatisfyRelationship)
    assert len(rels) == 1


def test_satisfy_dotted_source_path():
    model = parse(
        "package P { requirement <'R1'> A; part t { part array; } satisfy A by t.array; }"
    )
    rels = model.relationships(kind=SatisfyRelationship)
    assert len(rels) == 1
    assert model.resolve(rels[0].source).declared_name == "array"


def test_package_imports():
    model = parse("package Lib { part def W; }\npackage P { public import Lib::*; }")
    pkg = model.find(name="P")[0]
    assert pkg.imports == ["Lib::*"]  # type: ignore[attr-defined]


def test_documented_loss_dependency_statements():
    """Pinned upstream loss: dependency never reaches the visitor output.

    When this starts failing, sysmlpy fixed it - wire verify/derive through.
    """
    model = parse("package P { part b; requirement <'R1'> A; dependency b to A; }")
    kinds = {type(el).__name__ for el in model.iter_elements()}
    assert "DeriveRelationship" not in kinds
    assert "VerifyRelationship" not in kinds


def test_documented_loss_connection_endpoints():
    """Pinned upstream loss: connect endpoints are discarded by the visitor."""
    model = parse(
        "package P { part a { port pa; } part b { port pb; } connection c connect a.pa to b.pb; }"
    )
    conn = model.find(name="c")[0]
    assert conn.source is None  # type: ignore[attr-defined]
    assert conn.target is None  # type: ignore[attr-defined]


def test_builder_write_parse_round_trip_is_lossless_for_covered_subset():
    model = Model()
    pkg = builder.pkg(model, "Terminal")
    amp_def = builder.part_def(model, "Amplifier", owner=pkg)
    amp = builder.part(model, "amp", owner=pkg, definition=amp_def, multiplicity="[2]")
    builder.attr(model, "power", 52.0, owner=amp, unit="dBW")
    req = builder.req(
        model, "REQ-P", "PowerFloor", owner=pkg, text="Power shall exceed 50 dBW.", subject=amp
    )
    builder.satisfy(model, source=amp, target=req, owner=pkg)

    reparsed = backend.parse(write_model(model))
    entries = diff_models(model, reparsed, by_name=True)
    # provenance fields (source/confidence) do not exist in textual notation
    real = [e for e in entries if "source" not in e.detail or "->" not in e.detail]
    assert [e for e in real if e.kind in ("added", "removed")] == []

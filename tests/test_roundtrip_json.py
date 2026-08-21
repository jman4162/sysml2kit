"""Property test: json -> model -> json is a fixpoint for generated models."""

from hypothesis import given
from hypothesis import strategies as st

from sysml2kit.interchange import model_from_json, model_to_json
from sysml2kit.model import Model, builder

names = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1,
    max_size=12,
).map(lambda s: f"n{s}")


@st.composite
def models(draw) -> Model:
    model = Model()
    pkg = builder.pkg(model, draw(names))
    part_names = draw(st.lists(names, min_size=1, max_size=6, unique=True))
    parts = [builder.part(model, n, owner=pkg) for n in part_names]
    req_names = draw(st.lists(names, min_size=0, max_size=4, unique=True))
    reqs = [
        builder.req(model, f"REQ-{i:03d}", n, owner=pkg, text=draw(st.text(max_size=40)))
        for i, n in enumerate(req_names)
    ]
    for i, r in enumerate(reqs):
        builder.satisfy(model, source=parts[i % len(parts)], target=r, owner=pkg)
    for i, p in enumerate(parts):
        if draw(st.booleans()):
            builder.attr(
                model,
                f"a{i}",
                draw(st.floats(allow_nan=False, allow_infinity=False, width=32)),
                owner=p,
                unit=draw(st.sampled_from(["kg", "m", "GHz", "dB", None])),
            )
    return model


@given(models())
def test_json_model_json_fixpoint(model: Model):
    once = model_to_json(model)
    twice = model_to_json(model_from_json(once))
    assert once == twice

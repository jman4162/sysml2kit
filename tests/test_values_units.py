import pytest

from sysml2kit.model import AttributeValue
from sysml2kit.units import check_dimensionality, convert, is_valid_unit, parse_unit


def test_render_with_unit():
    assert AttributeValue(value=52.0, unit="dBW").render() == "52.0 [dBW]"


def test_render_string_quotes():
    assert AttributeValue(value="RHCP").render() == '"RHCP"'


def test_render_without_unit():
    assert AttributeValue(value=4).render() == "4"


def test_frozen():
    value = AttributeValue(value=1.0)
    with pytest.raises(Exception, match="frozen"):
        value.value = 2.0  # type: ignore[misc]


@pytest.mark.parametrize("unit", ["GHz", "dB", "dBW", "dBm", "dBi", "dBK", "kg", "km"])
def test_engineering_units_parse(unit):
    assert is_valid_unit(unit)


def test_unknown_unit_rejected():
    assert not is_valid_unit("blorps")
    with pytest.raises(ValueError, match="unparseable"):
        parse_unit("blorps")


def test_convert():
    assert convert(1.0, "km", "m") == pytest.approx(1000.0)


def test_dimensionality():
    assert check_dimensionality("GHz", "Hz")
    assert not check_dimensionality("GHz", "kg")

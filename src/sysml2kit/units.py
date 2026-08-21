"""Unit-string helpers backed by pint.

Models store units as text (round-trip fidelity with the textual notation);
these helpers check and convert them. A few decibel spellings common in
engineering practice are registered on top of pint's defaults.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pint

_EXTRA_DEFINITIONS = (
    # Referenced-quantity decibels: dimensionally plain decibels; the reference
    # (isotropic antenna, dipole, carrier, per-kelvin) is bookkeeping the model
    # keeps in the unit text.
    "dBi = decibel",
    "dBd = decibel",
    "dBc = decibel",
    "dBK = decibel",
)


@lru_cache(maxsize=1)
def registry() -> Any:
    """Return the shared pint unit registry (created on first use)."""
    reg: Any = pint.UnitRegistry()
    for definition in _EXTRA_DEFINITIONS:
        reg.define(definition)
    return reg


def parse_unit(text: str) -> Any:
    """Parse unit text into a pint unit; raises ValueError on unknown units."""
    try:
        return registry().Unit(text)
    except Exception as exc:
        raise ValueError(f"unparseable unit {text!r}: {exc}") from exc


def is_valid_unit(text: str) -> bool:
    """Return whether pint can parse this unit text."""
    try:
        parse_unit(text)
    except ValueError:
        return False
    return True


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value between two unit texts."""
    quantity = registry().Quantity(value, parse_unit(from_unit))
    return float(quantity.to(parse_unit(to_unit)).magnitude)


def check_dimensionality(unit_a: str, unit_b: str) -> bool:
    """Return whether two unit texts share a dimensionality."""
    return bool(parse_unit(unit_a).dimensionality == parse_unit(unit_b).dimensionality)

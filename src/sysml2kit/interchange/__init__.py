"""Systems Modeling API JSON interchange: the primary lossless format."""

from sysml2kit.interchange.reader import InterchangeError, model_from_json, record_to_element
from sysml2kit.interchange.writer import element_to_record, model_to_json, write_json

__all__ = [
    "InterchangeError",
    "element_to_record",
    "model_from_json",
    "model_to_json",
    "record_to_element",
    "write_json",
]

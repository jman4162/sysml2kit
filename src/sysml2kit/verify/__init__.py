"""Verification execution: bind analyses to engines, run them, check requirements."""

from sysml2kit.verify.binding import (
    BINDING_NAME,
    BindingError,
    VerificationBinding,
    build_payload,
    extract_bindings,
)
from sysml2kit.verify.engines import Engine, EngineNotFoundError, EngineRegistry
from sysml2kit.verify.runner import (
    AnalysisResult,
    RequirementVerdict,
    VerificationRun,
    apply_results,
    run_verification,
)

__all__ = [
    "BINDING_NAME",
    "AnalysisResult",
    "BindingError",
    "Engine",
    "EngineNotFoundError",
    "EngineRegistry",
    "RequirementVerdict",
    "VerificationBinding",
    "VerificationRun",
    "apply_results",
    "build_payload",
    "extract_bindings",
    "run_verification",
]

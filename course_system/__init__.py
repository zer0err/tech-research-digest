"""Deterministic course metadata validation and release gates."""

from .state import CourseState, InvalidTransition, transition
from .validate import ValidationIssue, assert_release_ready, validate_series

__all__ = [
    "CourseState",
    "InvalidTransition",
    "ValidationIssue",
    "assert_release_ready",
    "transition",
    "validate_series",
]

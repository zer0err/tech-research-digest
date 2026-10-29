from __future__ import annotations

from enum import StrEnum


class CourseState(StrEnum):
    PLANNED = "planned"
    SOURCED = "sourced"
    DRAFTED = "drafted"
    AI_CHECKED = "ai_checked"
    TESTED = "tested"
    RELEASE_CONFIRMED = "release_confirmed"
    PUBLISHED = "published"
    NEEDS_REVISION = "needs_revision"


class InvalidTransition(ValueError):
    """Raised when a course state attempts to skip or reverse a quality gate."""


_FORWARD: dict[CourseState, frozenset[CourseState]] = {
    CourseState.PLANNED: frozenset({CourseState.SOURCED}),
    CourseState.SOURCED: frozenset({CourseState.DRAFTED, CourseState.NEEDS_REVISION}),
    CourseState.DRAFTED: frozenset({CourseState.AI_CHECKED, CourseState.NEEDS_REVISION}),
    CourseState.AI_CHECKED: frozenset({CourseState.TESTED, CourseState.NEEDS_REVISION}),
    CourseState.TESTED: frozenset({CourseState.RELEASE_CONFIRMED, CourseState.NEEDS_REVISION}),
    CourseState.RELEASE_CONFIRMED: frozenset({CourseState.PUBLISHED, CourseState.NEEDS_REVISION}),
    CourseState.NEEDS_REVISION: frozenset({CourseState.SOURCED}),
    CourseState.PUBLISHED: frozenset(),
}


def transition(current: CourseState | str, target: CourseState | str) -> CourseState:
    """Validate and return a single explicit state transition.

    Published content is immutable in this state machine. A substantive correction
    starts a new content version at ``planned`` instead of rewriting history.
    """

    try:
        current_state = CourseState(current)
        target_state = CourseState(target)
    except ValueError as exc:
        raise InvalidTransition(f"unknown course state: {exc}") from exc

    if target_state not in _FORWARD[current_state]:
        raise InvalidTransition(f"cannot transition from {current_state} to {target_state}")
    return target_state

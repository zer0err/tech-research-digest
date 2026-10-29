from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit

from .state import CourseState

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_PYTHON = re.compile(r"^3\.\d+$")
_MODEL_ID = re.compile(r"^gpt-6(?:\.\d+)?(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?$")
_SERIES_FIELDS = frozenset({
    "schema_version",
    "series_id",
    "content_version",
    "title_zh",
    "title_en",
    "audience",
    "prerequisites",
    "final_outcome",
    "status",
    "release_confirmation",
    "environment",
    "sources",
    "lessons",
})


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str


class ReleaseGateError(ValueError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(summary)


def _required_text(value: Any, path: str, issues: list[ValidationIssue]) -> None:
    if not isinstance(value, str) or not value.strip():
        issues.append(ValidationIssue(path, "required_text", "must be a non-empty string"))


def _reject_unknown_keys(value: dict[str, Any], path: str, allowed: frozenset[str], issues: list[ValidationIssue]) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        issues.append(ValidationIssue(path, "unknown_keys", f"unknown fields: {unknown}"))


def _valid_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith(("Z", "+00:00")):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _validate_model_evidence(value: Any, path: str, issues: list[ValidationIssue]) -> None:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "type", "must be an object"))
        return
    _reject_unknown_keys(value, path, frozenset({"provider", "model_id", "completed_at", "result"}), issues)
    if value.get("provider") != "openai":
        issues.append(ValidationIssue(f"{path}.provider", "model_policy", "must be openai"))
    if not isinstance(value.get("model_id"), str) or not _MODEL_ID.fullmatch(value["model_id"]):
        issues.append(ValidationIssue(f"{path}.model_id", "model_policy", "must identify a GPT-6-family model"))
    if not _valid_datetime(value.get("completed_at")):
        issues.append(ValidationIssue(f"{path}.completed_at", "format", "must be an ISO-8601 UTC timestamp"))
    if value.get("result") != "passed":
        issues.append(ValidationIssue(f"{path}.result", "gate", "must equal passed"))


def validate_series(series: Any, *, for_release: bool = False) -> list[ValidationIssue]:
    """Validate course metadata without reading or publishing draft lesson bodies."""

    issues: list[ValidationIssue] = []
    if not isinstance(series, dict):
        return [ValidationIssue("$", "type", "series must be an object")]
    _reject_unknown_keys(series, "$", _SERIES_FIELDS, issues)

    if series.get("schema_version") != 1:
        issues.append(ValidationIssue("schema_version", "unsupported", "must equal 1"))

    series_id = series.get("series_id")
    if not isinstance(series_id, str) or not _ID.fullmatch(series_id):
        issues.append(ValidationIssue("series_id", "format", "must be a lowercase kebab-case identifier"))

    version = series.get("content_version")
    if not isinstance(version, str) or not _SEMVER.fullmatch(version):
        issues.append(ValidationIssue("content_version", "format", "must use semantic version x.y.z"))

    for field in ("title_zh", "title_en", "audience", "prerequisites", "final_outcome"):
        _required_text(series.get(field), field, issues)

    try:
        state = CourseState(series.get("status"))
    except (TypeError, ValueError):
        state = None
        issues.append(ValidationIssue("status", "enum", "is not a supported course state"))

    environment = series.get("environment")
    if not isinstance(environment, dict):
        issues.append(ValidationIssue("environment", "type", "must be an object"))
    else:
        _reject_unknown_keys(
            environment,
            "environment",
            frozenset({"python", "os", "package_manager", "lockfile", "test_command"}),
            issues,
        )
        python_version = environment.get("python")
        if not isinstance(python_version, str) or not _PYTHON.fullmatch(python_version):
            issues.append(ValidationIssue("environment.python", "format", "must be a pinned Python minor such as 3.12"))
        for field in ("os", "package_manager", "lockfile", "test_command"):
            _required_text(environment.get(field), f"environment.{field}", issues)

    release_confirmation = series.get("release_confirmation")
    if release_confirmation is not None:
        if not isinstance(release_confirmation, dict):
            issues.append(ValidationIssue("release_confirmation", "type", "must be null or an object"))
        else:
            _reject_unknown_keys(
                release_confirmation,
                "release_confirmation",
                frozenset({"confirmed_at", "note"}),
                issues,
            )
            if not _valid_datetime(release_confirmation.get("confirmed_at")):
                issues.append(ValidationIssue(
                    "release_confirmation.confirmed_at",
                    "format",
                    "must be an ISO-8601 UTC timestamp",
                ))
            _required_text(release_confirmation.get("note"), "release_confirmation.note", issues)

    lessons = series.get("lessons")
    if not isinstance(lessons, list) or not 1 <= len(lessons) <= 30:
        issues.append(ValidationIssue("lessons", "length", "must contain between 1 and 30 lessons"))
        lessons = []

    lesson_ids: set[str] = set()
    ordinals: set[int] = set()
    expected_version = series.get("content_version")
    for index, lesson in enumerate(lessons):
        path = f"lessons[{index}]"
        if not isinstance(lesson, dict):
            issues.append(ValidationIssue(path, "type", "must be an object"))
            continue
        _reject_unknown_keys(
            lesson,
            path,
            frozenset({
                "lesson_id",
                "ordinal",
                "title",
                "content_version",
                "status",
                "required",
                "estimated_minutes",
                "generation",
                "ai_check",
                "test_evidence",
                "source_ids",
                "exercises",
            }),
            issues,
        )
        lesson_id = lesson.get("lesson_id")
        if not isinstance(lesson_id, str) or not _ID.fullmatch(lesson_id):
            issues.append(ValidationIssue(f"{path}.lesson_id", "format", "must be lowercase kebab-case"))
        elif lesson_id in lesson_ids:
            issues.append(ValidationIssue(f"{path}.lesson_id", "duplicate", "must be unique in the series"))
        else:
            lesson_ids.add(lesson_id)
        ordinal = lesson.get("ordinal")
        if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 1:
            issues.append(ValidationIssue(f"{path}.ordinal", "format", "must be a positive integer"))
        elif ordinal in ordinals:
            issues.append(ValidationIssue(f"{path}.ordinal", "duplicate", "must be unique in the series"))
        else:
            ordinals.add(ordinal)
        _required_text(lesson.get("title"), f"{path}.title", issues)
        estimated_minutes = lesson.get("estimated_minutes")
        if (
            not isinstance(estimated_minutes, int)
            or isinstance(estimated_minutes, bool)
            or estimated_minutes <= 0
        ):
            issues.append(ValidationIssue(f"{path}.estimated_minutes", "range", "must be a positive integer; 120 is an editorial target"))
        exercises = lesson.get("exercises")
        if not isinstance(exercises, list) or not exercises:
            issues.append(ValidationIssue(f"{path}.exercises", "required", "must contain at least one exercise"))
            exercises = []
        exercise_ids = set()
        for exercise_index, exercise in enumerate(exercises):
            exercise_path = f"{path}.exercises[{exercise_index}]"
            if not isinstance(exercise, dict):
                issues.append(ValidationIssue(exercise_path, "type", "must be an object"))
                continue
            _reject_unknown_keys(exercise, exercise_path, frozenset({"exercise_id", "title", "required"}), issues)
            exercise_id = exercise.get("exercise_id")
            if not isinstance(exercise_id, str) or not _ID.fullmatch(exercise_id):
                issues.append(ValidationIssue(f"{exercise_path}.exercise_id", "format", "must be lowercase kebab-case"))
            elif exercise_id in exercise_ids:
                issues.append(ValidationIssue(f"{exercise_path}.exercise_id", "duplicate", "must be unique within the lesson"))
            else:
                exercise_ids.add(exercise_id)
            _required_text(exercise.get("title"), f"{exercise_path}.title", issues)
            if exercise.get("required") is not True:
                issues.append(ValidationIssue(f"{exercise_path}.required", "unsupported", "must be true"))
        if lesson.get("content_version") != expected_version:
            issues.append(ValidationIssue(f"{path}.content_version", "mismatch", "must match the series version"))
        try:
            lesson_state = CourseState(lesson.get("status"))
        except (TypeError, ValueError):
            lesson_state = None
            issues.append(ValidationIssue(f"{path}.status", "enum", "is not a supported course state"))
        source_ids = lesson.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or not all(isinstance(item, str) and item for item in source_ids):
            issues.append(ValidationIssue(f"{path}.source_ids", "required", "must contain at least one source ID"))
        if lesson.get("required") is not True:
            issues.append(ValidationIssue(f"{path}.required", "unsupported", "stage 1 only supports required lessons"))
        _validate_model_evidence(lesson.get("generation"), f"{path}.generation", issues)
        _validate_model_evidence(lesson.get("ai_check"), f"{path}.ai_check", issues)
        test_evidence = lesson.get("test_evidence")
        if not isinstance(test_evidence, dict):
            issues.append(ValidationIssue(f"{path}.test_evidence", "type", "must be an object"))
        else:
            _reject_unknown_keys(
                test_evidence,
                f"{path}.test_evidence",
                frozenset({"command", "completed_at", "result"}),
                issues,
            )
            environment_command = environment.get("test_command") if isinstance(environment, dict) else None
            if test_evidence.get("command") != environment_command:
                issues.append(ValidationIssue(
                    f"{path}.test_evidence.command",
                    "mismatch",
                    "must match environment.test_command",
                ))
            if test_evidence.get("result") != "passed":
                issues.append(ValidationIssue(f"{path}.test_evidence.result", "gate", "must equal passed"))
            if not _valid_datetime(test_evidence.get("completed_at")):
                issues.append(ValidationIssue(
                    f"{path}.test_evidence.completed_at",
                    "format",
                    "must be an ISO-8601 UTC timestamp",
                ))
        if for_release and lesson_state not in {CourseState.RELEASE_CONFIRMED, CourseState.PUBLISHED}:
            issues.append(ValidationIssue(f"{path}.status", "release_gate", "lesson is not release-confirmed"))

    if ordinals and ordinals != set(range(1, len(lessons) + 1)):
        issues.append(ValidationIssue("lessons[].ordinal", "sequence", "ordinals must be contiguous from 1"))

    sources = series.get("sources")
    if not isinstance(sources, list) or not sources:
        issues.append(ValidationIssue("sources", "required", "must contain at least one source"))
        sources = []
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        path = f"sources[{index}]"
        if not isinstance(source, dict):
            issues.append(ValidationIssue(path, "type", "must be an object"))
            continue
        _reject_unknown_keys(
            source,
            path,
            frozenset({"source_id", "title", "publisher", "url", "license", "accessed_at"}),
            issues,
        )
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not _ID.fullmatch(source_id):
            issues.append(ValidationIssue(f"{path}.source_id", "format", "must be lowercase kebab-case"))
        elif source_id in source_ids:
            issues.append(ValidationIssue(f"{path}.source_id", "duplicate", "must be unique"))
        else:
            source_ids.add(source_id)
        for field in ("title", "publisher", "license", "accessed_at"):
            _required_text(source.get(field), f"{path}.{field}", issues)
        if not _valid_url(source.get("url")):
            issues.append(ValidationIssue(f"{path}.url", "format", "must be an absolute HTTPS URL"))
        if not _valid_date(source.get("accessed_at")):
            issues.append(ValidationIssue(f"{path}.accessed_at", "format", "must be an ISO-8601 date"))

    for index, lesson in enumerate(lessons):
        if isinstance(lesson, dict) and isinstance(lesson.get("source_ids"), list):
            unknown = set(lesson["source_ids"]) - source_ids
            if unknown:
                issues.append(ValidationIssue(f"lessons[{index}].source_ids", "reference", f"unknown source IDs: {sorted(unknown)}"))

    if for_release:
        if state != CourseState.RELEASE_CONFIRMED:
            issues.append(ValidationIssue("status", "release_gate", "series must be release_confirmed"))
        if release_confirmation is None:
            issues.append(ValidationIssue(
                "release_confirmation",
                "release_gate",
                "series release confirmation is required",
            ))
    return issues


def assert_release_ready(series: Any) -> None:
    issues = validate_series(series, for_release=True)
    if issues:
        raise ReleaseGateError(issues)

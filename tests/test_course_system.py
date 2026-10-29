from __future__ import annotations

import copy
import json
import re
import subprocess
from pathlib import Path

import pytest

from course_system.state import CourseState, InvalidTransition, transition
from course_system.validate import ReleaseGateError, assert_release_ready, validate_series

FIXTURE = Path(__file__).parent / "course_fixtures" / "valid_series.json"
SCHEMA = Path(__file__).parents[1] / "course_system" / "schemas" / "series.schema.json"


def load_series() -> dict:
    return json.loads(FIXTURE.read_text())


def test_forward_state_machine_requires_every_gate() -> None:
    state = CourseState.PLANNED
    for expected in (
        CourseState.SOURCED,
        CourseState.DRAFTED,
        CourseState.AI_CHECKED,
        CourseState.TESTED,
        CourseState.RELEASE_CONFIRMED,
        CourseState.PUBLISHED,
    ):
        state = transition(state, expected)
    assert state is CourseState.PUBLISHED


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (CourseState.PLANNED, CourseState.TESTED),
        (CourseState.DRAFTED, CourseState.PUBLISHED),
        (CourseState.TESTED, CourseState.PUBLISHED),
        (CourseState.PUBLISHED, CourseState.DRAFTED),
    ],
)
def test_state_machine_rejects_skips_and_rewrites(current: CourseState, target: CourseState) -> None:
    with pytest.raises(InvalidTransition):
        transition(current, target)


def test_revision_returns_to_sourcing() -> None:
    assert transition(CourseState.AI_CHECKED, CourseState.NEEDS_REVISION) is CourseState.NEEDS_REVISION
    assert transition(CourseState.NEEDS_REVISION, CourseState.SOURCED) is CourseState.SOURCED


def test_valid_fixture_is_release_ready() -> None:
    series = load_series()
    assert validate_series(series) == []
    assert_release_ready(series)


def test_incomplete_lesson_blocks_whole_series() -> None:
    series = load_series()
    series["lessons"][1]["status"] = "tested"
    with pytest.raises(ReleaseGateError) as error:
        assert_release_ready(series)
    assert any(issue.code == "release_gate" and issue.path == "lessons[1].status" for issue in error.value.issues)


def test_series_confirmation_is_required() -> None:
    series = load_series()
    series["status"] = "tested"
    with pytest.raises(ReleaseGateError) as error:
        assert_release_ready(series)
    assert any(issue.path == "status" and issue.code == "release_gate" for issue in error.value.issues)


def test_missing_publisher_confirmation_blocks_release() -> None:
    series = load_series()
    series["release_confirmation"] = None
    with pytest.raises(ReleaseGateError) as error:
        assert_release_ready(series)
    assert any(issue.path == "release_confirmation" for issue in error.value.issues)


def test_duplicate_and_non_contiguous_lessons_fail() -> None:
    series = load_series()
    series["lessons"][1]["lesson_id"] = series["lessons"][0]["lesson_id"]
    series["lessons"][1]["ordinal"] = 4
    issues = validate_series(series)
    assert any(issue.code == "duplicate" and issue.path.endswith("lesson_id") for issue in issues)
    assert any(issue.code == "sequence" for issue in issues)


def test_unknown_source_and_version_mismatch_fail() -> None:
    series = copy.deepcopy(load_series())
    series["lessons"][0]["source_ids"] = ["missing-source"]
    series["lessons"][0]["content_version"] = "2.0.0"
    issues = validate_series(series)
    assert any(issue.code == "reference" for issue in issues)
    assert any(issue.code == "mismatch" for issue in issues)


def test_https_sources_are_required() -> None:
    series = load_series()
    series["sources"][0]["url"] = "http://example.test/course"
    assert any(issue.path.endswith(".url") for issue in validate_series(series))


def test_non_gpt6_generation_model_is_rejected() -> None:
    series = load_series()
    series["lessons"][0]["generation"]["model_id"] = "gpt-oss-20b"
    issues = validate_series(series)
    assert any(issue.path == "lessons[0].generation.model_id" for issue in issues)


def test_failed_check_or_test_blocks_series() -> None:
    series = load_series()
    series["lessons"][0]["ai_check"]["result"] = "failed"
    series["lessons"][1]["test_evidence"]["result"] = "failed"
    issues = validate_series(series)
    assert any(issue.path == "lessons[0].ai_check.result" for issue in issues)
    assert any(issue.path == "lessons[1].test_evidence.result" for issue in issues)


@pytest.mark.parametrize("minutes", [0, -1, True, 1.5, "120", None])
def test_lesson_duration_must_be_a_positive_integer(minutes: object) -> None:
    series = load_series()
    series["lessons"][0]["estimated_minutes"] = minutes
    issues = validate_series(series)
    assert any(issue.path == "lessons[0].estimated_minutes" for issue in issues)


@pytest.mark.parametrize("minutes", [30, 60, 120, 180])
def test_two_hour_estimate_is_not_an_invented_release_limit(minutes: int) -> None:
    series = load_series()
    series["lessons"][0]["estimated_minutes"] = minutes
    assert validate_series(series) == []


@pytest.mark.parametrize("model_id", ["gpt-6", "gpt-6-astra", "gpt-6.1-sol", "gpt-6.1-terra", "gpt-6-future-model"])
def test_model_family_does_not_hardcode_variant_names(model_id: str) -> None:
    series = load_series()
    for field in ("generation", "ai_check"):
        series["lessons"][0][field]["model_id"] = model_id
    assert validate_series(series) == []
    pattern = json.loads(SCHEMA.read_text())["$defs"]["model_evidence"]["properties"]["model_id"]["pattern"]
    assert re.fullmatch(pattern, model_id)


@pytest.mark.parametrize("model_id", ["gpt-60", "gpt-5.6-sol", "mimo-v2.6-flash", "gpt-oss-20b", "gpt-6/other", None])
def test_non_family_or_malformed_model_ids_remain_rejected(model_id: object) -> None:
    series = load_series()
    series["lessons"][0]["generation"]["model_id"] = model_id
    assert any(issue.path == "lessons[0].generation.model_id" for issue in validate_series(series))


def test_gpt6_name_does_not_allow_another_provider() -> None:
    series = load_series()
    series["lessons"][0]["generation"]["provider"] = "other"
    assert any(issue.path == "lessons[0].generation.provider" for issue in validate_series(series))


@pytest.mark.parametrize("exercises", [
    None, [], {}, [None], [{"exercise_id": "../unsafe", "title": "Task", "required": True}],
    [{"exercise_id": "ex-01", "title": "", "required": True}],
    [{"exercise_id": "ex-01", "title": "Task", "required": False}],
    [{"exercise_id": "ex-01", "title": "Task", "required": 1}],
    [{"exercise_id": "ex-01", "title": "Task", "required": True, "secret": "not-permitted"}],
    [{"exercise_id": "ex-01", "title": "Task", "required": True},
     {"exercise_id": "ex-01", "title": "Different task", "required": True}],
])
def test_every_lesson_requires_safe_unique_exercises(exercises: object) -> None:
    series = load_series()
    series["lessons"][0]["exercises"] = exercises
    issues = validate_series(series)
    assert any(issue.path.startswith("lessons[0].exercises") for issue in issues)
    with pytest.raises(ReleaseGateError):
        assert_release_ready(series)


def test_exercise_schema_and_validator_share_required_contract() -> None:
    schema = json.loads(SCHEMA.read_text())
    assert "exercises" in schema["$defs"]["lesson"]["required"]
    assert schema["$defs"]["lesson"]["properties"]["exercises"]["minItems"] == 1
    assert set(schema["$defs"]["exercise"]["required"]) == {"exercise_id", "title", "required"}
    assert schema["$defs"]["exercise"]["properties"]["required"] == {"const": True}
    assert schema["$defs"]["lesson"]["properties"]["estimated_minutes"] == {"type": "integer", "minimum": 1}


def test_test_evidence_must_use_series_command() -> None:
    series = load_series()
    series["lessons"][0]["test_evidence"]["command"] = "pytest tests/one.py"
    issues = validate_series(series)
    assert any(issue.path == "lessons[0].test_evidence.command" for issue in issues)


def test_local_draft_directory_is_git_ignored() -> None:
    root = Path(__file__).parents[1]
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "course_work/example/metadata.json"],
        cwd=root,
        check=False,
    )
    assert result.returncode == 0


def test_schema_is_valid_json_and_forbids_unknown_properties() -> None:
    schema = json.loads(SCHEMA.read_text())
    assert schema["additionalProperties"] is False
    assert "release_confirmation" in schema["required"]


def test_unknown_metadata_fields_are_rejected() -> None:
    series = load_series()
    series["lessons"][0]["unknown_field"] = True
    issues = validate_series(series)
    assert any(issue.code == "unknown_keys" and issue.path == "lessons[0]" for issue in issues)

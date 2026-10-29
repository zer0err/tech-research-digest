# Course system

This package contains deterministic metadata and release gates for VORASIO course series. It does not generate lessons, call a model, encrypt drafts, or publish content.

## Workflow

1. Draft lessons stay under the Git-ignored `course_work/` directory.
2. Each lesson records its source IDs, estimated duration, GPT-6 generation/check evidence, and passing executable-test evidence.
3. The complete series advances through `planned`, `sourced`, `drafted`, `ai_checked`, `tested`, `release_confirmed`, and finally `published`.
4. A series can pass the release gate only when every required lesson is release-confirmed and the publisher confirmation exists.
5. Publishing is a single manual operation after the whole series passes. There is no course cron or background service.

## Validate metadata

```bash
python -m course_system.cli tests/course_fixtures/valid_series.json
python -m course_system.cli tests/course_fixtures/valid_series.json --release
```

The fixture is synthetic metadata used only for tests. It is not course content and must not be presented as a published curriculum.

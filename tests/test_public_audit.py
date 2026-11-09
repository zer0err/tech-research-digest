import json

from research_bot.audit import public_summaries


def test_public_summary_excludes_raw_text_and_stale_files(tmp_path):
    source, output = tmp_path / "reports", tmp_path / "public"
    source.mkdir()
    output.mkdir()
    (output / "decision-old.json").write_text("private old data")
    (source / "decision-test.json").write_text(json.dumps({
        "slot": "model_research", "reason": "analysis_rejected", "usable": 3,
        "issues": ["unpublished draft"], "error": "private error", "prompt": "private prompt",
    }))
    (source / "draft.md").write_text("unpublished content")
    public_summaries(source, output)
    assert sorted(p.name for p in output.iterdir()) == ["decision-test.json"]
    assert json.loads((output / "decision-test.json").read_text()) == {
        "slot": "model_research", "reason": "analysis_rejected", "usable": 3,
    }


def test_public_summary_skips_malformed_and_non_public_values(tmp_path):
    source = tmp_path / "reports"
    source.mkdir()
    (source / "decision-broken.json").write_text("not json")
    (source / "decision-list.json").write_text("[]")
    (source / "decision-invalid.json").write_text(json.dumps({"slot": "private prose here", "reason": "ok"}))
    output = tmp_path / "public"
    public_summaries(source, output)
    assert not list(output.iterdir())

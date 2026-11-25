"""Recorded wording regression, offline through the production collector."""
from datetime import datetime, timedelta

import pytest

from research_bot import rotation_collect
from research_bot.core import Item
from research_bot.rotation_claims import rotation_claim_issues
from research_bot.schedule import ZONE


CUTOFF = datetime(2026, 11, 25, 17, tzinfo=ZONE)
BIOLOOM = (
    "Using Loom52M, BioLoom achieves 56.82% domain-balanced mean accuracy across 67 zero-shot tasks, "
    "compared with 48.77% for MedPMC-CLIP."
)
ONE_TAKE = (
    "The paired-view benchmark lowers perceptual error by 59%, landmark error by 56%, and speech leakage "
    "by 97% relative to the strongest baseline, Wan 3.0."
)
FARMSENSE = (
    "FarmSense combines a cloud Groq API model, image recognition, multilingual speech interaction "
    "and a Gradio interface. Its goal is to make agricultural advice more accessible."
)
DEPLOYMENT = (
    "We deployed and evaluated the complete system on low-end devices, measuring latency "
    "and memory during normal operation."
)
BAD_BIO = "仅提供摘要，缺乏实验细节与对比基线；证据等级 C"
BAD_ONE = "摘要中未给出具体基线模型与数据集规模；证据等级 B"
BAD_FARM = "证明多模态框架可在低端设备上部署，适合农业数字化推广，但需实地验证"
GOOD = (
    "摘要点名 MedPMC-CLIP；未提供基线实现细节。",
    "摘要点名 Wan 3.0；未给出数据集规模。",
    "能否在低端设备部署仍待验证；当前系统使用云端推理。",
)


def report(rows=GOOD):
    return f"""## 本期结论

- 该研究介绍了新的生物医学图文方法 [1]
- 该研究介绍了视角切换方法 [2]
- 农业咨询系统整合图像与语音处理 [3]

## 逐项分析

| 资料 | 局限与工程意义 |
| --- | --- |
| [1] BioLoom | {rows[0]} |
| [2] One Take | {rows[1]} |
| [3] FarmSense | {rows[2]} |

## 工程行动建议

先分别核对各份资料的评估口径，再决定是否设计工程实验。工程实验应记录目标场景和关键假设，避免将完成的研究演示与真实部署条件混为一谈。后续应独立验证适用设备、语言范围、网络条件、使用成本和用户反馈，并把适用性限制明确写入报告。

## 参考资料

- [1] BioLoom
- [2] One Take
- [3] FarmSense
"""


def item(index, summary):
    # Sorted selection preserves this explicit citation order and stable cutoff.
    return Item(str(index), ("BioLoom", "One Take", "FarmSense")[index - 1],
                f"https://example.com/{index}", (CUTOFF - timedelta(hours=index)).isoformat(), summary, "Fixture")


@pytest.mark.parametrize(("rows", "evidence", "expected"), [
    ((BAD_BIO, GOOD[1], GOOD[2]), (BIOLOOM, ONE_TAKE, FARMSENSE), ["false_missing_comparator"]),
    ((GOOD[0], BAD_ONE, GOOD[2]), (BIOLOOM, ONE_TAKE, FARMSENSE), ["false_missing_comparator"]),
    ((GOOD[0], GOOD[1], BAD_FARM), (BIOLOOM, ONE_TAKE, FARMSENSE), ["unsupported_proven_deployment"]),
    ((BAD_BIO, BAD_ONE, BAD_FARM), (BIOLOOM, ONE_TAKE, FARMSENSE),
     ["false_missing_comparator", "unsupported_proven_deployment"]),
    (GOOD, (BIOLOOM, ONE_TAKE, FARMSENSE), []),
    ((GOOD[0], BAD_ONE, GOOD[2]), (BIOLOOM, FARMSENSE, FARMSENSE), []),
    ((GOOD[0], GOOD[1], BAD_FARM), (BIOLOOM, ONE_TAKE, DEPLOYMENT), []),
    ((GOOD[0], "该资料另有设备实验。", BAD_FARM), (BIOLOOM, DEPLOYMENT, FARMSENSE), ["unsupported_proven_deployment"]),
    ((GOOD[0], GOOD[1], "尚未证明能在低端设备部署。"), (BIOLOOM, ONE_TAKE, FARMSENSE), []),
])
def test_rotation_collector_claim_gate(rows, evidence, expected, monkeypatch):
    items = [item(i, summary) for i, summary in enumerate(evidence, 1)]
    monkeypatch.setattr(rotation_collect, "collect", lambda *_: items)
    monkeypatch.setattr(rotation_collect, "groq_analyse", lambda *_: report(rows))
    outcome = rotation_collect.generate("multimodal", CUTOFF, set())
    assert outcome.get("issues", []) == expected
    assert outcome["reason"] == ("analysis_rejected" if expected else "prepared")
    if expected:
        assert not outcome["items"] and not outcome["report"]


def test_body_citation_not_reference_list_sets_scope():
    summary = [BIOLOOM, FARMSENSE]
    assert rotation_claim_issues("未给出基线模型。[1]\n\n## 参考资料\n[2]", summary) == [
        "false_missing_comparator",
    ]
    assert rotation_claim_issues("未给出基线模型。[2]\n\n## 参考资料\n[1]", summary) == []
    assert rotation_claim_issues("## 参考资料\n未给出基线模型。[1]", summary) == []


def test_generic_baseline_and_unmeasured_potential_are_not_evidence():
    assert rotation_claim_issues(
        "[1] 未给出具体基线模型。", ["We compared with state-of-the-art solutions."],
    ) == []
    assert rotation_claim_issues(
        "[1] 证明可在低端设备部署。",
        ["Future work may evaluate deployment on low-end devices."],
    ) == ["unsupported_proven_deployment"]



def test_named_comparator_does_not_supply_missing_implementation_details():
    for phrase in ("未提供基线模型的实现细节", "未给出基线模型的参数"):
        assert rotation_claim_issues("[1] " + phrase, [BIOLOOM]) == []


def test_later_method_name_is_not_baseline():
    assert rotation_claim_issues(
        "[1] 未说明具体基线模型",
        ["We compared with unnamed methods and then used BioLoom to analyze the results."],
    ) == []


def test_later_qualification_cannot_clear_existing_proof_claim():
    assert rotation_claim_issues(
        "[1] 证明可在低端设备上部署，但未经验证", [FARMSENSE],
    ) == ["unsupported_proven_deployment"]

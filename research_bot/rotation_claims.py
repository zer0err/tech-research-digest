"""Narrow, source-scoped contradictions in the Plan B research draft."""
from __future__ import annotations

import re
import unicodedata

from markdown_it import MarkdownIt

_MARKDOWN = MarkdownIt("commonmark", {"html": False}).enable("table")
_CITE = re.compile(r"\[(\d+)\](?!\()")
_SENTENCE = re.compile(r"(?<!\d)\.(?=\s|$)|\.(?=\s+[A-Z])|[。！？；;\n]")
_MISSING_BASELINE = re.compile(
    r"(?:未(?:给出|提供|报告|说明|列出|披露|注明|提及|明确)|没有|缺(?:乏|少|失)|无(?:明确|具体)?)"
    r"[^。！？；;，,|]{0,38}(?:对比基线|比较基线|基线(?:模型|名称)?|对照模型)(?!(?:的)?(?:数据|规模|配置|细节|实现|代码|超参数|分数|结果|指标|版本))"
    r"|(?:does not (?:name|identify|give|report)|no (?:named |comparison )?|lacks? (?:a |named )?)\s*(?:comparison )?(?:baseline models?|baselines?)\b",
    re.I,
)
_COMPARE = re.compile(
    r"\b(?:compared (?:with|to|against)|relative to|versus|vs\.?|outperforms?|"
    r"(?:competing|strongest|evaluated) baselines?)\b|相比|优于|相较|对比基线",
    re.I,
)
# Deliberately require a recognizable model/release identifier alongside a comparison cue.
_MODEL = re.compile(r"\b(?:[A-Za-z][\w.-]*-[A-Za-z][\w.-]*|[A-Z][a-z]+[A-Z][A-Za-z]+|[A-Z][A-Za-z]+[ \t]+\d+(?:\.\d+)+)\b")
_NEGATIVE_EVIDENCE = re.compile(
    r"\b(?:no|not|never|unavailable|planned|future work|potential|may|could)\b|未(?:经|有|报告|测试|评估|部署)|尚未|计划|拟|待验证",
    re.I,
)
_LOW_END = re.compile(
    r"低端(?:设备|终端|手机|硬件)|低功耗(?:设备|终端|硬件)|入门(?:级)?(?:设备|手机|终端)|"
    r"资源受限(?:的)?(?:设备|终端|硬件)|\b(?:low[- ]end|low[- ]power|entry[- ]level|resource[- ]constrained)"
    r" (?:devices?|hardware|phones?|handsets?|terminals?)\b",
    re.I,
)
_PROVEN = re.compile(r"(?:证明|证实|验证|实测|已(?:成功|实际)?(?:部署|运行))|\b(?:proved?|demonstrated?|verified|validated|tested|deployed)\b", re.I)
_DEPLOY = re.compile(r"部署|运行|落地|\b(?:deploy(?:ed|ment)?|run(?:s|ning)?|ran|execut(?:e[ds]?|ion))\b", re.I)
_EVALUATED = re.compile(
    r"实测|测试|评估|部署验证|报告[^。]{0,18}(?:延迟|时延|内存|功耗|帧率)|"
    r"\b(?:measured|tested|evaluated|benchmark(?:ed|ing)?|latency|memory|throughput|frame rate|energy use)\b",
    re.I,
)
_QUALIFIED = re.compile(
    r"^(?:(?:尚|仍|还|暂)?未|不能|无法|需(?:要)?|有待|拟|建议|可考虑|计划|待|"
    r"(?:the (?:paper|study) )?(?:did not|does not|cannot|not yet|future work|we plan to)\b)"
    r"|(?:未(?:能|经|有|见)?(?:证明|证实|验证|实测|部署|评估)|没有(?:证明|验证|实测)|"
    r"(?:需|待)验证[^。]*?(?:能否|是否)|\b(?:does not|did not|not yet|has not)\b)",
    re.I,
)


def _text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).translate(str.maketrans("‐‑–—", "----"))


def _sentences(value: str) -> list[str]:
    return [s.strip(" *:：-") for s in _SENTENCE.split(_text(value)) if s.strip()]


def _named_baseline(summary: str) -> bool:
    for sentence in _sentences(summary):
        if _NEGATIVE_EVIDENCE.search(sentence):
            continue
        for cue in _COMPARE.finditer(sentence):
            # A method name before a cue isn't evidence of a named comparison target.
            tail = sentence[cue.end():cue.end() + 105]
            if any(any(c.isupper() or c.isdecimal() for c in match.group()) for match in _MODEL.finditer(tail)):
                return True
    return False


def _evaluated_deployment(summary: str) -> bool:
    return any(_LOW_END.search(sentence) and _DEPLOY.search(sentence) and _EVALUATED.search(sentence)
               and not _NEGATIVE_EVIDENCE.search(sentence) for sentence in _sentences(summary))


def _claims(report: str):
    """Yield individual body phrases with their paragraph or row's citations."""
    row = None
    cell = None
    for token in _MARKDOWN.parse(report):
        if token.type == "tr_open":
            row = []
        elif token.type in {"th_open", "td_open"}:
            cell = ""
        elif token.type == "inline":
            if cell is not None:
                cell = token.content
            else:
                for phrase in _sentences(token.content):
                    yield phrase, _CITE.findall(phrase) or _CITE.findall(token.content)
        elif token.type in {"th_close", "td_close"}:
            if row is not None and cell is not None:
                row.append(cell)
            cell = None
        elif token.type == "tr_close" and row is not None:
            inherited = _CITE.findall(row[0]) if row else []
            for value in row:
                for phrase in _sentences(value):
                    yield phrase, _CITE.findall(phrase) or inherited
            row = None


def rotation_claim_issues(report: str, summaries: list[str]) -> list[str]:
    body = re.split(r"(?m)^## 参考资料\s*$", report, maxsplit=1)[0]
    issues = set()
    named = [_named_baseline(summary) for summary in summaries]
    evaluated = [_evaluated_deployment(summary) for summary in summaries]
    for phrase, numbers in _claims(body):
        refs = {int(i) - 1 for i in numbers if 0 < int(i) <= len(summaries)}
        # Treat only an unambiguous attribution as evidence of contradiction.
        if len(refs) == 1 and _MISSING_BASELINE.search(phrase) and named[next(iter(refs))]:
            issues.add("false_missing_comparator")
        # “仍待验证” is not proof. Remove that qualified span only, so
        # “证明……但仍待验证” is rejected for its independent proof assertion.
        assertion = re.sub(r"(?:仍|尚|还)?待验证", "", phrase)
        if _LOW_END.search(phrase) and _DEPLOY.search(phrase) and _PROVEN.search(assertion):
            if not _QUALIFIED.search(phrase) and (not refs or not any(evaluated[i] for i in refs)):
                issues.add("unsupported_proven_deployment")
    return sorted(issues)

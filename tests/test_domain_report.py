from dataclasses import asdict

from research_bot import domain_report
from research_bot.core import REPORT_HEADINGS, Item, report_validation_errors


def evidence():
    return {'agents': [asdict(Item('a', '工具规范', 'https://example.com/a', '2026-11-09', '工具调用规范。', 'fixture'))]}


def report():
    return '\n\n'.join(h + '\n\n' + '依据资料核查工具接入条件与能力边界。[1]' * 5 for h in REPORT_HEADINGS['domain'])


def test_missing_evidence_never_calls_model(tmp_path, monkeypatch):
    def fail(*a, **kw):
        raise AssertionError('must not call')
    monkeypatch.setattr(domain_report, 'groq_analyse', fail)
    result = domain_report.build({}, tmp_path, generate=True)
    assert len(result) == 10
    assert all(r['status'] == 'needs_evidence' for r in result.values())


def test_checkpoint_reuses_valid_content_but_regenerates_changed_evidence(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(domain_report, 'groq_analyse', lambda *a, **kw: calls.append(a) or report())
    assert domain_report.build(evidence(), tmp_path, generate=True)['agents']['status'] == 'generated'
    domain_report.build(evidence(), tmp_path, generate=True)
    assert len(calls) == 1
    changed = evidence()
    changed['agents'][0]['summary'] = '更新后的工具规范。'
    domain_report.build(changed, tmp_path, generate=True)
    assert len(calls) == 2


def test_invalid_citations_rejected():
    items = [Item(**evidence()['agents'][0])]
    assert 'invalid_source_numbers' in report_validation_errors(report() + '\n错误引用 [99]', items, 'domain')


def test_failed_module_preserves_other_module_results(tmp_path, monkeypatch):
    data = evidence()
    data['models'] = data['agents']
    def generate(title, *a, **kw):
        if title == domain_report.MODULES['models']:
            raise RuntimeError('fixture')
        return report()
    monkeypatch.setattr(domain_report, 'groq_analyse', generate)
    result = domain_report.build(data, tmp_path, generate=True)
    assert result['models']['status'] == 'failed'
    assert result['agents']['status'] == 'generated'

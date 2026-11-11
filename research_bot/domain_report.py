"""Local, resumable domain reports from explicitly assigned evidence packets."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .core import Item, groq_analyse, normalize_report, report_validation_errors

MODULES = {
    'models': '基础模型与能力',
    'training': '训练方法与数据',
    'inference': '推理系统与计算效率',
    'agents': 'Agent 与工具生态',
    'knowledge': '知识增强与信息处理',
    'multimodal': '多模态生成与交互',
    'robotics': '具身智能与机器人',
    'evaluation': '评测、可靠性与安全',
    'applications': '产品、应用与商业化',
    'infrastructure': '开发生态与产业基础',
}


def build(evidence: dict, output: Path, *, generate: bool = False, provider: str = 'groq',
          selected: list[str] | None = None) -> dict:
    unknown = set(evidence) - MODULES.keys()
    if unknown:
        raise ValueError(f'Unknown modules: {sorted(unknown)}')
    if selected and set(selected) - MODULES.keys():
        raise ValueError('Unknown selected module')
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / 'manifest.json'
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest = {}
    for key, title in MODULES.items():
        items = [Item(**entry) for entry in evidence.get(key, [])]
        fingerprint = hashlib.sha256(json.dumps(
            {'items': [asdict(i) for i in items], 'provider': provider, 'schema': 1},
            ensure_ascii=False, sort_keys=True,
        ).encode()).hexdigest()
        path = output / f'{key}.md'
        record = {'title': title, 'sources': len(items), 'fingerprint': fingerprint, 'status': 'needs_evidence'}
        previous = old.get(key, {})
        if items:
            valid_old = (previous.get('fingerprint') == fingerprint and previous.get('status') == 'generated'
                         and path.exists() and not report_validation_errors(path.read_text(), items, 'domain'))
            if valid_old:
                record['status'] = 'generated'
            elif generate and (not selected or key in selected):
                try:
                    report = normalize_report(groq_analyse(title, '围绕本模块的问题综合证据，明确资料边界。',
                                                          items, 'domain', provider=provider), 'domain', items)
                    issues = report_validation_errors(report, items, 'domain')
                    if len(report) < 300 or '降级为' in report:
                        issues.append('insufficient_or_truncated')
                    if issues:
                        (output / f'{key}.rejected.md').write_text(report)
                        record.update(status='rejected', issues=issues)
                    else:
                        path.write_text(report)
                        record['status'] = 'generated'
                except Exception as exc:
                    record.update(status='failed', error=type(exc).__name__)
            else:
                record['status'] = 'ready'
        manifest[key] = record
        # Checkpoint after each module, so interrupted runs can resume.
        temp = output / 'manifest.tmp'
        temp.write_text(json.dumps({**old, **manifest}, ensure_ascii=False, indent=2))
        temp.replace(manifest_path)
    lines = ['# AI 领域报告覆盖总览', '',
             '> generated 仅表示生成并通过结构检查，不代表事实已人工核实。缺少资料的模块不得视为已覆盖。', '',
             '| 模块 | 来源数 | 状态 | 内容 |', '|---|---:|---|---|']
    for key, record in manifest.items():
        link = f'[阅读]({key}.md)' if record['status'] == 'generated' else '—'
        lines.append(f"| {record['title']} | {record['sources']} | {record['status']} | {link} |")
    (output / 'index.md').write_text('\n'.join(lines) + '\n')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, help='JSON: module ID -> list of Item dictionaries')
    parser.add_argument('--output', type=Path, default=Path('outputs/ai-domain'))
    parser.add_argument('--generate', action='store_true', help='Call configured model; default only audits coverage')
    parser.add_argument('--provider', choices=['groq', 'mimo'], default='groq')
    parser.add_argument('--modules', nargs='+', choices=list(MODULES), help='Generate only selected modules')
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text()) if args.evidence else {}
    result = build(evidence, args.output, generate=args.generate, provider=args.provider, selected=args.modules)
    print(json.dumps({key: r['status'] for key, r in result.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

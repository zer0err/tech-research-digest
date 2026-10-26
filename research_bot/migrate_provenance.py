"""Idempotently add provenance to saved pages without regenerating their text."""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .provenance import metadata, render
from .site import render_index


def main():
    entries = json.loads(Path('docs/posts.json').read_text())
    state = json.loads(Path('state/seen.json').read_text())
    publications = {urlsplit(url).path.split('/posts/')[-1]: record
                    for url, record in state.get('publications', {}).items()}
    confirmed_mimo = {'20261025-paper_brief.html', '20261025-core_research.html', '20261025-dev_practice.html'}
    for entry in entries:
        path = Path('docs') / entry['url']
        record = publications.get(path.name, {})
        analysis = record.get('analysis')
        if path.name in confirmed_mimo:
            analysis = {'provider': 'Xiaomi MiMo', 'model': 'mimo-v2.6-flash',
                        'verified_run': '40259668432'}
        if entry['topic'] == 'daily_digest':
            analysis = {'provider': '程序汇总（未调用 AI）', 'model': '不适用'}
        data = entry.get('provenance') or metadata(record.get('items', []), analysis)
        entry['provenance'] = data
        page = path.read_text()
        page = re.sub(r'<!-- provenance:start -->.*?<!-- provenance:end -->', '', page, flags=re.S)
        page = re.sub(r'(</h1>)', lambda match, data=data: match.group(1) + render(data), page, count=1)
        path.write_text(page)
    Path('docs/posts.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n')
    render_index(entries)


if __name__ == '__main__':
    main()

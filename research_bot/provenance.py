"""Safe public provenance: facts from publication records, not model-generated claims."""
import html
from urllib.parse import urlsplit


def metadata(items, analysis=None):
    sources = []
    for item in items:
        if item is None:
            continue
        raw = item if isinstance(item, dict) else vars(item)
        url = str(raw.get('url', ''))
        if urlsplit(url).scheme != 'https':
            continue
        host = urlsplit(url).hostname or ''
        family = ('书目索引' if 'openalex' in host or 'crossref' in str(raw.get('source', '')).lower()
                  else '论文/预印本' if any(domain in host for domain in ['arxiv.org', 'aclanthology.org', 'thecvf.com', 'doi.org'])
                  else '代码与版本' if host in {'github.com', 'api.github.com'} else '博客/公开网页')
        sources.append({key: str(value) for key, value in {
            'title': raw.get('title', ''), 'url': url, 'publisher': raw.get('source', host), 'host': host,
            'family': family, 'published': raw.get('published', '未记录'),
            'date_precision': raw.get('date_precision', '未记录'), 'doi': raw.get('doi', ''),
            'kind': raw.get('kind', '未记录'),
        }.items()})
    return {'analysis': analysis or {'provider': '历史记录未确认', 'model': '未记录'}, 'sources': sources}


def render(data):
    def esc(value):
        return html.escape(str(value), quote=True)
    ai = data.get('analysis', {})
    provider = ai.get('provider', '历史记录未确认')
    model = ai.get('model', '未记录')
    if provider == '程序汇总（未调用 AI）':
        label = '程序汇总 · 未使用 AI 分析'
    elif provider in {'历史记录未确认', '未记录'}:
        label = 'AI 分析：历史记录未确认'
    else:
        label = 'AI 分析：' + str(provider)
    detail = f' title="{esc(model)}"' if model and model not in {'未记录', '不适用'} else ''
    return '<!-- provenance:start --><p class="ai-analysis"' + detail + '>' + esc(label) + '</p><!-- provenance:end -->'

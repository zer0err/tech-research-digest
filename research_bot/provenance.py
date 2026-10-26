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
    sources = data.get('sources', [])
    rows = ''.join(
        f'<li><a href="{esc(s["url"])}" rel="noopener">[{i}] {esc(s["title"])}</a>'
        f'<dl><dt>来源</dt><dd>{esc(s["publisher"])} · {esc(s["host"])}</dd>'
        f'<dt>类型</dt><dd>{esc(s["family"])}</dd><dt>原始日期</dt><dd>{esc(s["published"])}</dd>'
        f'<dt>日期精度</dt><dd>{esc(s["date_precision"])}</dd>'
        + (f'<dt>DOI</dt><dd>{esc(s["doi"])}</dd>' if s.get('doi') else '') + '</dl></li>'
        for i, s in enumerate(sources, 1)
    )
    return ('<!-- provenance:start --><section class="source-provenance" aria-label="信息来源与分析记录">'
            '<dl><dt>分析服务</dt><dd>' + esc(ai.get('provider', '未记录')) + '</dd>'
            '<dt>分析模型</dt><dd>' + esc(ai.get('model', '未记录')) + '</dd>'
            '<dt>证据范围</dt><dd>采集的摘要、公开页面或版本说明；不代表已阅读全文、独立复现或人工审校。</dd></dl>'
            '<details><summary>信息来源 · ' + str(len(sources)) + ' 项（展开查看）</summary>'
            + ('<ol>' + rows + '</ol>' if rows else '<p>未保留逐项来源记录，请查看正文参考资料；站内日报来源为正文列出的站内文章。</p>')
            + '</details></section><!-- provenance:end -->')

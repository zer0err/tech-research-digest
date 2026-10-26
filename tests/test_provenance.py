from research_bot.provenance import metadata, render


def test_provenance_escapes_sources_and_drops_unsafe_urls():
    data = metadata([{'title': '<script>', 'url': 'https://arxiv.org/abs/123', 'source': 'arXiv'},
                     {'title': 'bad', 'url': 'javascript:alert(1)'}], {'provider': 'MiMo', 'model': 'mimo-v2.6-flash'})
    assert len(data['sources']) == 1
    text = render(data)
    assert '&lt;script&gt;' in text
    assert 'javascript:' not in text
    assert 'mimo-v2.6-flash' in text


def test_missing_historical_model_is_explicit_not_invented():
    assert '历史记录未确认' in render(metadata([]))

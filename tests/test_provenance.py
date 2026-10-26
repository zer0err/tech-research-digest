from research_bot.provenance import metadata, render


def test_provenance_escapes_sources_and_drops_unsafe_urls():
    data = metadata([{'title': '<script>', 'url': 'https://arxiv.org/abs/123', 'source': 'arXiv'},
                     {'title': 'bad', 'url': 'javascript:alert(1)'}], {'provider': 'MiMo', 'model': 'mimo-v2.6-flash'})
    assert len(data['sources']) == 1
    text = render(data)
    assert '<script>' not in text
    assert 'javascript:' not in text
    assert 'mimo-v2.6-flash' in text
    assert '信息来源' not in text
    assert '<details>' not in text


def test_missing_historical_model_is_explicit_not_invented():
    assert '历史记录未确认' in render(metadata([]))


def test_future_provider_is_rendered_without_hardcoded_brand_list():
    text = render(metadata([], {'provider': 'Future AI', 'model': 'new-model'}))
    assert 'AI 分析：Future AI</p>' in text
    assert 'title="new-model"' in text


def test_digest_is_not_mislabeled_as_ai_generated():
    assert '未使用 AI 分析' in render(metadata([], {'provider': '程序汇总（未调用 AI）', 'model': '不适用'}))

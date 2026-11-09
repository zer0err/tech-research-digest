from research_bot.growth import load_config, render_growth_pages, whatsapp_url


def test_safe_config(tmp_path):
    assert load_config(tmp_path / 'missing.json') == {}
    path = tmp_path / 'growth.json'
    path.write_text('{broken')
    assert load_config(path) == {}
    path.write_text('[]')
    assert load_config(path) == {}


def test_whatsapp_only_valid_configured_number():
    assert whatsapp_url({}) == ''
    assert whatsapp_url({'whatsapp_number': 'javascript:alert(1)'}) == ''
    assert whatsapp_url({'whatsapp_number': '+12345678901'}) == 'https://wa.me/12345678901'


def test_official_business_link_is_preserved_without_number(tmp_path):
    link = 'https://wa.me/message/RX4QLFUUD5UCL1'
    config = {'whatsapp_link': link}
    assert whatsapp_url(config) == link
    render_growth_pages(config, tmp_path)
    page = (tmp_path / 'services.html').read_text()
    assert f'data-whatsapp href="{link}"' in page
    assert 'WhatsApp 联系入口待配置' not in page
    assert '?text=' not in page
    for bad in ('javascript:alert(1)', link + '?text=private', link + '#fragment',
                'https://wa.me.evil.test/message/code', 'https://wa.me/message/', 'https://wa.me/1234'):
        assert whatsapp_url({'whatsapp_link': bad}) == ''


def test_pages_without_contact_do_not_fake_submission(tmp_path):
    render_growth_pages({}, tmp_path)
    consult = (tmp_path / 'consult.html').read_text()
    assert 'WhatsApp 联系入口待配置' in consult
    assert 'data-whatsapp' not in consult
    assert '<form id="project-brief"' in consult
    assert ' action=' not in consult
    assert 'href="feed.xml"' in (tmp_path / 'subscribe.html').read_text()
    assert '不上传到本站服务器' in (tmp_path / 'privacy.html').read_text()


def test_configured_contact_is_manual_handoff(tmp_path):
    render_growth_pages({'whatsapp_number': '+12345678901'}, tmp_path)
    consult = (tmp_path / 'consult.html').read_text()
    assert 'https://wa.me/12345678901' in consult
    assert '?text=' not in consult
    assert '不会自动发送消息' in consult


def test_no_script_fields_disabled_and_services_alias(tmp_path):
    render_growth_pages({}, tmp_path)
    services = (tmp_path / 'services.html').read_text()
    assert '<fieldset disabled data-brief-fields>' in services
    assert services == (tmp_path / 'consult.html').read_text()
    assert 'href="services.html"' in (tmp_path / 'subscribe.html').read_text()


def test_javascript_uses_path_only_and_no_remote_submission():
    from pathlib import Path

    script = Path('docs/assets/growth.js').read_text()
    assert 'source.origin === location.origin ? source.pathname' in script
    assert 'event.preventDefault()' in script
    assert 'fetch(' not in script
    assert 'localStorage' not in script
    assert '?text=' not in script

"""Theme tokens and button text stay readable in light and dark mode."""
from __future__ import annotations

import re
from pathlib import Path

ASSETS = Path('docs/assets')


def _channel(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _normalize(hex_color: str) -> str:
    raw = hex_color.lstrip('#').lower()
    if len(raw) == 3:
        raw = ''.join(ch * 2 for ch in raw)
    return raw


def _luminance(hex_color: str) -> float:
    raw = _normalize(hex_color)
    rgb = [int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = (_channel(channel) for channel in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(foreground: str, background: str) -> float:
    lighter = max(_luminance(foreground), _luminance(background))
    darker = min(_luminance(foreground), _luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def _tokens(css: str) -> tuple[dict[str, str], dict[str, str]]:
    blocks = re.findall(r':root\s*\{([^}]*)\}', css)
    assert len(blocks) >= 2

    def parse(block: str) -> dict[str, str]:
        return {name: _normalize(value) for name, value in re.findall(r'--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})', block)}

    return parse(blocks[0]), parse(blocks[1])


def _mix(paper: str, ink: str, paper_share: float) -> str:
    def channels(hex_color: str) -> list[int]:
        raw = _normalize(hex_color)
        return [int(raw[i:i + 2], 16) for i in (0, 2, 4)]

    mixed = [round(channels(paper)[i] * paper_share + channels(ink)[i] * (1 - paper_share)) for i in range(3)]
    return ''.join(f'{channel:02x}' for channel in mixed)


def test_shared_tokens_meet_text_and_ui_contrast():
    light, dark = _tokens((ASSETS / 'style.css').read_text())
    course_light, course_dark = _tokens((ASSETS / 'course.css').read_text())
    for name in ('paper', 'surface', 'ink', 'muted', 'line', 'line-strong', 'soft'):
        assert course_light[name] == light[name]
        assert course_dark[name] == dark[name]
    for name in ('accent', 'accent-hover', 'on-accent'):
        assert course_light[name] == light[name]
        assert course_dark[name] == dark[name]
    assert course_light['accent'] == course_light['green']
    assert course_dark['accent'] == course_dark['green']

    for theme in (light, dark):
        for background in ('paper', 'surface', 'soft'):
            assert contrast(theme['ink'], theme[background]) >= 4.5
            assert contrast(theme['muted'], theme[background]) >= 4.5
            assert contrast(theme['line-strong'], theme[background]) >= 3
        assert contrast(theme['on-accent'], theme['accent']) >= 4.5
        assert contrast(theme['on-accent'], theme['accent-hover']) >= 4.5


def test_inverted_card_colors_follow_theme_variables():
    css = (ASSETS / 'style.css').read_text()
    assert '#cfcfcf' not in css and '#d4d4d4' not in css and '#ffffff33' not in css
    light, dark = _tokens(css)
    for label, minimum in (('card-topic', 4.5), ('card-summary', 4.5), ('card-meta', 3)):
        match = re.search(
            rf'\.featured \.{label} \{{[^}}]*color(?:-mix\(in srgb, var\(--paper\) (\d+)%, var\(--ink\)\))',
            css,
        )
        assert match, label
        share = int(match.group(1)) / 100
        for theme in (light, dark):
            assert contrast(_mix(theme['paper'], theme['ink'], share), theme['ink']) >= minimum


def test_solid_buttons_keep_on_accent_text():
    css = (ASSETS / 'growth.css').read_text()
    assert '.growth-card a:not(.growth-button):not(.growth-primary)' in css
    assert '.growth-button:visited' in css
    assert 'a.growth-button:visited' in css or '.growth-button:visited' in css
    button = re.search(r'\.growth-button,\s*\.growth-primary \{([^}]*)\}', css)
    assert button and 'color: var(--on-accent)' in button.group(1)
    assert 'background: var(--accent)' in button.group(1)

"""Preserve historical editions and distinguish B's planned and actual times."""

import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree.ElementTree import fromstring

from research_bot.daily import render_daily_page
from research_bot.timeline import render_timeline


def test_rotation_article_shows_planned_and_actual_assembly():
    scheduled = datetime.fromisoformat("2026-11-24T18:00:00+08:00")
    actual = datetime.fromisoformat("2026-11-24T18:26:10+08:00")
    canonical = "posts/20261124-daily.html"
    page = render_daily_page("本期日报", actual, [], [], {},
                             "本期未收录：训练方法与数据。", canonical, scheduled_at=scheduled)
    assert "实际合成时间" in page
    assert "2026-11-24 18:26 · Asia/Taipei（UTC+8）" in page
    assert "计划合成时间" in page
    assert "2026-11-24 18:00 · Asia/Taipei（UTC+8）" in page
    assert 'data-published-at="2026-11-24T18:26:10+08:00"' in page
    assert '"datePublished": "2026-11-24T18:26:10+08:00"' in page
    assert '<link rel="canonical" href="https://vorasio.com/posts/20261124-daily.html">' in page
    assert "本期未收录：训练方法与数据。" in page
    assert "assets/article.js?v=reading-1" in page


def test_rotation_archive_rss_and_status_keep_historical_identity(monkeypatch, tmp_path):
    from research_bot import schedule

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://vorasio.com")
    monkeypatch.setattr(schedule, "daily_planned_time", lambda day: "18:00")
    Path("docs/posts").mkdir(parents=True)
    old_path = Path("docs/posts/20261116-daily.html")
    old_contents = b"<html><body>Historical issue sentinel.</body></html>"
    old_path.write_bytes(old_contents)
    legacy = {"topic": "daily_report", "status": "published", "count": 1, "title": "往期",
              "date": "2026-11-16T09:00:00+08:00", "url": "posts/20261116-daily.html"}
    rotated = {"topic": "daily_report", "status": "published", "count": 1, "title": "轮转",
               "date": "2026-11-24T18:26:10+08:00", "url": "posts/20261124-daily.html",
               "scheduled_at": "2026-11-24T18:00:00+08:00", "rotation": True}
    render_timeline([legacy])
    assert 'data-planned-time="18:00"' in Path("docs/index.html").read_text()
    render_timeline([legacy, rotated])
    page = Path("docs/index.html").read_text()
    assert "发布时间：2026-11-16 09:00 · Asia/Taipei（UTC+8）" in page
    assert "实际合成时间：2026-11-24 18:26 · Asia/Taipei（UTC+8）；计划合成时间：18:00" in page
    assert "18:00 计划合成" in page
    assert "18:00 计划合成" in Path("docs/about.html").read_text()
    assert old_path.read_bytes() == old_contents
    assert json.loads(Path("docs/posts.json").read_text()) == [rotated, legacy]
    items = fromstring(Path("docs/feed.xml").read_bytes()).findall("./channel/item")
    for entry, item in zip([rotated, legacy], items, strict=True):
        assert item.findtext("guid") == item.findtext("link") == "https://vorasio.com/" + entry["url"]
        assert parsedate_to_datetime(item.findtext("pubDate")) == datetime.fromisoformat(entry["date"])

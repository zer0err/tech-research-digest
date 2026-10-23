from datetime import UTC, datetime

import httpx

from research_bot.core import item_id, title_key
from research_bot.sources import PaperHTML, crossref_entries, date_parts, fetch_entries, inverse_abstract


def test_openalex_abstract_and_doi_identity():
    assert inverse_abstract({"world": [1], "Hello": [0]}) == "Hello world"
    assert inverse_abstract(None) == ""
    assert item_id({"doi": "https://doi.org/10.1/ABC"}) == item_id({"doi": "10.1/abc"})
    assert title_key("AI: Model!") == title_key("AI Model")


def test_crossref_uses_publication_not_index_timestamp():
    entry = crossref_entries({"message": {"items": [{"DOI": "10.1/test", "title": ["Paper"],
        "published": {"date-parts": [[2024, 2]]}, "indexed": {"date-time": "2026-10-23"}}]}})[0]
    assert entry["published"].startswith("2024-02-01")
    assert entry["date_precision"] == "month"
    assert entry["summary"] == ""
    assert date_parts([2026, 13]) == ("", "unknown")


def test_paper_html_extracts_only_abstract():
    page = PaperHTML()
    page.feed('<meta name="citation_title" content="Real paper"><div id="abstract">Actual <b>abstract</b>.</div><p>Not abstract</p>')
    assert page.meta["citation_title"] == "Real paper"
    assert "Not abstract" not in " ".join(page.abstract)
    assert "abstract" in " ".join(page.abstract)


def test_openalex_key_in_header_not_url(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-key"
        assert "test-key" not in str(request.url)
        assert "from_publication_date" in request.url.params["filter"]
        return httpx.Response(200, json={"results": []})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert fetch_entries({"type": "openalex", "url": "https://api.openalex.org/works", "query": "AI"},
                             client, datetime(2026, 10, 23, tzinfo=UTC), datetime(2026, 10, 20, tzinfo=UTC)) == []


def test_cvf_old_archive_does_not_become_daily_news():
    def handler(request):
        raise AssertionError("An old archive should not be fetched for today's news")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert fetch_entries({"type": "cvf", "url": "https://openaccess.thecvf.com/CVPR2026", "published": "2026-05-23", "name": "CVF"},
                             client, datetime(2026, 10, 23, tzinfo=UTC), datetime(2026, 10, 20, tzinfo=UTC)) == []


def test_github_skips_drafts_and_prereleases(monkeypatch):
    monkeypatch.setenv("GH_SOURCE_TOKEN", "test-token")
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(200, json=[{"id": 1, "html_url": "https://github.com/a/b/releases/tag/v1", "body": "Changes"},
                                         {"id": 2, "draft": True}, {"id": 3, "prerelease": True}])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        records = fetch_entries({"type": "github", "url": "https://api.github.com/repos/a/b/releases"},
                                client, datetime.now(UTC), datetime.now(UTC))
    assert len(records) == 1
    assert records[0]["title"].startswith("a/b:")


def test_acl_uses_paper_date_not_rss_correction(monkeypatch):
    monkeypatch.setattr("research_bot.sources.time.sleep", lambda _: None)
    feed = '''<rss version="2.0"><channel><title>ACL</title><link>https://aclanthology.org</link><description>ACL</description>
      <item><title>Person</title><link>https://aclanthology.org/people/a/</link></item>
      <item><title>Paper</title><link>https://aclanthology.org/2025.acl-long.1/</link>
      <pubDate>Fri, 23 Oct 2026 00:00:00 GMT</pubDate></item>
    </channel></rss>'''
    def handler(request):
        if request.url.path == "/index.xml":
            return httpx.Response(200, text=feed)
        assert request.url.path == "/2025.acl-long.1/"
        return httpx.Response(200, text='<meta name="citation_publication_date" content="2025/07/01">'
                              '<div class="acl-abstract">Original abstract</div>')
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        records = fetch_entries({"type": "acl", "url": "https://aclanthology.org/index.xml"}, client,
                                datetime(2026, 10, 23, tzinfo=UTC), datetime(2025, 1, 1, tzinfo=UTC))
    assert len(records) == 1
    assert records[0]["published"].startswith("2025-07-01")
    assert records[0]["summary"] == "Original abstract"


def test_source_tokens_not_sent_to_other_hosts(monkeypatch):
    import pytest
    monkeypatch.setenv("OPENALEX_API_KEY", "secret")
    monkeypatch.setenv("GH_SOURCE_TOKEN", "secret")
    with httpx.Client(transport=httpx.MockTransport(lambda _: (_ for _ in ()).throw(AssertionError()))) as client:
        for kind in ("openalex", "github"):
            with pytest.raises(ValueError):
                fetch_entries({"type": kind, "url": "https://example.com/"}, client, datetime.now(UTC), datetime.now(UTC))


def test_metadata_search_drops_non_ai_model_results(monkeypatch):
    import research_bot.core as core
    monkeypatch.setattr(core, "fetch_entries", lambda *args: [
        {"id": "clinical", "title": "Clinical prediction model", "published": "2026-10-23",
         "summary": "A health belief model and clinical survival model.", "link": "https://example.com/clinical"},
        {"id": "llm", "title": "Training language models", "published": "2026-10-23",
         "summary": "A transformer neural network training method.", "link": "https://example.com/llm"},
    ])
    records = core.collect({"lookback_hours": 72, "keywords": ["model", "transformer"],
                            "sources": [{"name": "Crossref", "type": "crossref", "url": "https://api.crossref.org/works"}]},
                           datetime(2026, 10, 23, 12, tzinfo=UTC))
    assert len(records) == 1
    assert records[0].title == "Training language models"

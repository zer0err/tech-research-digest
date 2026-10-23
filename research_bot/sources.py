"""Small adapters for selected public sources; returned text is untrusted data."""
from __future__ import annotations

import logging
import os
import re
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

import feedparser
import httpx

LOG = logging.getLogger(__name__)


class SourceNotConfigured(RuntimeError):
    pass


def get(client: httpx.Client, url: str, *, params: dict | None = None, headers: dict | None = None) -> httpx.Response:
    for attempt in range(3):
        try:
            response = client.get(url, params=params, headers=headers)
            if getattr(response, "status_code", 200) not in {429, 500, 502, 503, 504} or attempt == 2:
                response.raise_for_status()
                return response
            delay = response.headers.get("retry-after", "")
            time.sleep(min(45, float(delay) if delay.replace(".", "", 1).isdigit() else 3 * 2**attempt))
        except httpx.TransportError:
            if attempt == 2:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Source request failed")


def date_parts(parts: list[int]) -> tuple[str, str]:
    if not parts or not 1900 <= parts[0] <= 2100:
        return "", "unknown"
    month, day = (parts[1] if len(parts) > 1 else 1), (parts[2] if len(parts) > 2 else 1)
    precision = "day" if len(parts) >= 3 else ("month" if len(parts) == 2 else "year")
    try:
        return datetime(parts[0], month, day, tzinfo=UTC).isoformat(), precision
    except ValueError:
        return "", "unknown"


def inverse_abstract(index: dict[str, list[int]] | None) -> str:
    if not isinstance(index, dict):
        return ""
    words = sorted((position, word) for word, positions in index.items() for position in positions if 0 <= position < 20000)
    return " ".join(word for _, word in words)


def openalex_entries(data: dict) -> list[dict]:
    entries = []
    for work in data.get("results", []):
        ids = work.get("ids") or {}
        location = work.get("primary_location") or {}
        doi = work.get("doi") or ids.get("doi") or ""
        entries.append({
            "id": work.get("id"), "doi": doi, "title": work.get("title", ""),
            "link": doi or location.get("landing_page_url") or work.get("id", ""),
            "published": work.get("publication_date"), "summary": inverse_abstract(work.get("abstract_inverted_index")),
        })
    return entries


def crossref_entries(data: dict) -> list[dict]:
    entries = []
    for work in data.get("message", {}).get("items", []):
        parts = (work.get("published") or work.get("published-online") or work.get("published-print") or {}).get("date-parts", [[]])
        published, precision = date_parts(parts[0])
        doi = work.get("DOI", "")
        entries.append({
            "id": doi, "doi": doi, "title": (work.get("title") or [""])[0],
            "link": "https://doi.org/" + doi if doi else work.get("URL", ""),
            "published": published, "date_precision": precision, "summary": work.get("abstract", ""),
        })
    return entries


class PaperHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.abstract: list[str] = []
        self.depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "meta":
            self.meta[str(values.get("name", "")).lower()] = str(values.get("content", ""))
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if self.depth and tag not in {"br", "img", "meta", "input", "link", "hr"}:
            self.depth += 1
        elif values.get("id") == "abstract" or "acl-abstract" in str(values.get("class", "")):
            self.depth = 1

    def handle_endtag(self, tag: str) -> None:
        if self.depth and tag not in {"br", "img", "meta", "input", "link", "hr"}:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.abstract.append(data)


def paper_page(client: httpx.Client, url: str) -> PaperHTML:
    parsed = PaperHTML()
    parsed.feed(get(client, url).text)
    return parsed


def fetch_entries(source: dict[str, Any], client: httpx.Client, now: datetime, cutoff: datetime) -> list[dict]:
    kind = source.get("type", "rss")
    url = source["url"]
    limit = int(source.get("limit", 20))
    if kind == "openalex":
        if urlsplit(url).hostname != "api.openalex.org":
            raise ValueError("OpenAlex credentials require the official API host")
        key = os.getenv("OPENALEX_API_KEY", "")
        if not key:
            raise SourceNotConfigured("OPENALEX_API_KEY is not configured")
        params = {
            "search": source["query"], "filter": f"from_publication_date:{cutoff:%Y-%m-%d},to_publication_date:{now:%Y-%m-%d}",
            "sort": "publication_date:desc", "per_page": min(limit, 50),
        }
        return openalex_entries(get(client, url, params=params, headers={"Authorization": f"Bearer {key}"}).json())
    if kind == "crossref":
        params = {
            "query.bibliographic": source["query"], "rows": min(limit, 30), "sort": "published", "order": "desc",
            "filter": f"from-pub-date:{cutoff:%Y-%m-%d},until-pub-date:{now:%Y-%m-%d}",
        }
        return crossref_entries(get(client, url, params=params).json())
    if kind == "cvf":
        # Conference archive publication day comes from CVF's conference index, never crawl time.
        published = datetime.fromisoformat(source["published"]).replace(tzinfo=UTC)
        if published < cutoff or published > now:
            LOG.info("CVF archive outside date window: %s", source["name"])
            return []
        listing = paper_page(client, url)
        links = list(dict.fromkeys(urljoin(url, link) for link in listing.links if link.endswith("_paper.html")))
        if not links:
            raise ValueError("CVF listing contained no paper links")
        entries = []
        for link in links[:limit]:
            if urlsplit(link).hostname != "openaccess.thecvf.com":
                continue
            time.sleep(1)
            page = paper_page(client, link)
            entries.append({
                "id": link, "title": page.meta.get("citation_title", ""), "link": link,
                "published": source["published"], "date_precision": "archive",
                "summary": " ".join(page.abstract), "doi": page.meta.get("citation_doi", ""),
            })
        return entries
    if kind == "github":
        if urlsplit(url).hostname != "api.github.com":
            raise ValueError("GitHub credentials require the official API host")
        headers = {"Accept": "application/vnd.github+json"}
        if token := os.getenv("GH_SOURCE_TOKEN", ""):
            headers["Authorization"] = f"Bearer {token}"
        records = get(client, url, params={"per_page": limit}, headers=headers).json()
        return [
            {"id": str(record["id"]), "title": record.get("name") or record.get("tag_name", ""),
             "link": record["html_url"], "published": record.get("published_at"), "summary": record.get("body", "")}
            for record in records if not record.get("draft") and not record.get("prerelease")
        ]
    parsed = feedparser.parse(get(client, url).content)
    if parsed.bozo and not parsed.entries:
        raise ValueError("Invalid source feed")
    if kind != "acl":
        return list(parsed.entries)
    entries = []
    checked = 0
    for entry in parsed.entries:
        link = entry.get("link", "")
        path = urlsplit(link).path.strip("/")
        if not re.fullmatch(r"\d{4}\.[\w-]+\.\d+", path) or urlsplit(link).hostname != "aclanthology.org":
            continue
        # The RSS can announce corrections to old papers: its timestamp is not their publication date.
        if int(path[:4]) < cutoff.year:
            continue
        if checked >= limit:
            break
        checked += 1
        time.sleep(1)
        page = paper_page(client, link)
        raw = page.meta.get("citation_publication_date", "")
        numbers = [int(value) for value in re.findall(r"\d+", raw)]
        date, precision = date_parts(numbers)
        entries.append({
            "id": link, "title": page.meta.get("citation_title") or entry.get("title", ""), "link": link,
            "published": date, "date_precision": precision, "summary": " ".join(page.abstract),
            "doi": page.meta.get("citation_doi", ""),
        })
    return entries

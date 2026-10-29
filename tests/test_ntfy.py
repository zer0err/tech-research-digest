from __future__ import annotations

import httpx
import pytest

from research_bot import core


def test_ntfy_is_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    assert core.send_ntfy("hello") is False


def test_ntfy_publishes_private_topic_and_click_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NTFY_TOPIC", "private_topic_12345678")
    sent: list[tuple[str, dict, dict]] = []

    def post(self, url, **kwargs):
        sent.append((url, kwargs["json"], kwargs["headers"]))
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", post)
    assert core.send_ntfy("新文章", title="研究简报", click_url="https://vorasio.com/posts/example.html")
    assert sent == [
        (
            "https://ntfy.sh",
            {
                "topic": "private_topic_12345678",
                "title": "研究简报",
                "message": "新文章",
                "priority": 3,
                "tags": ["newspaper"],
                "click": "https://vorasio.com/posts/example.html",
            },
            {},
        )
    ]


@pytest.mark.parametrize("topic", ["short", "bad/topic", "topic with spaces"])
def test_ntfy_rejects_unsafe_topic(monkeypatch: pytest.MonkeyPatch, topic: str) -> None:
    monkeypatch.setenv("NTFY_TOPIC", topic)
    with pytest.raises(ValueError, match="NTFY_TOPIC"):
        core.send_ntfy("hello")


def test_ntfy_uses_optional_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NTFY_TOPIC", "private_topic_12345678")
    monkeypatch.setenv("NTFY_TOKEN", "tk_example")

    def post(self, url, **kwargs):
        assert kwargs["headers"] == {"Authorization": "Bearer tk_example"}
        return httpx.Response(202, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", post)
    assert core.send_ntfy("hello") is True

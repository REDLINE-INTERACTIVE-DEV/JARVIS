"""Small dependency-light web search adapter for JARVIS."""
from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote

import httpx


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str

    def as_dict(self) -> dict[str, str]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


class ResearchEngine:
    """Web search with a replaceable provider and conservative defaults."""

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = max(2.0, min(float(timeout), 30.0))
        self.base_url = os.getenv(
            "JARVIS_SEARCH_URL",
            "https://html.duckduckgo.com/html/?q=",
        )

    @staticmethod
    def should_search(message: str) -> bool:
        text = message.strip().lower()
        return (
            text.startswith("search:")
            or text.startswith("search for ")
            or text.startswith("look up ")
            or text.startswith("/search ")
        )

    @staticmethod
    def clean_query(message: str) -> str:
        text = message.strip()
        lowered = text.lower()
        for prefix in ("search:", "search for ", "look up ", "/search "):
            if lowered.startswith(prefix):
                return text[len(prefix):].strip()
        return text

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        query = query.strip()
        if not query:
            raise ValueError("search query is required")
        limit = max(1, min(int(limit), 10))

        response = httpx.get(
            f"{self.base_url}{quote(query)}",
            headers={"User-Agent": "JARVIS/0.4 (+local-first assistant)"},
            timeout=self.timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        return self._parse_html(response.text, limit)

    @staticmethod
    def _parse_html(document: str, limit: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        pattern = re.compile(
            r'<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(document):
            raw_url, raw_title = match.groups()
            title = re.sub(r"<[^>]+>", "", raw_title)
            title = html.unescape(re.sub(r"\s+", " ", title)).strip()
            url = html.unescape(unquote(raw_url)).strip()
            if not url.startswith(("http://", "https://")):
                continue

            tail = document[match.end():match.end() + 1200]
            snippet_match = re.search(
                r'class=["\'][^"\']*result__snippet[^"\']*["\'][^>]*>(.*?)</',
                tail,
                re.IGNORECASE | re.DOTALL,
            )
            snippet = ""
            if snippet_match:
                snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1))
                snippet = html.unescape(re.sub(r"\s+", " ", snippet)).strip()

            results.append(SearchResult(title=title, url=url, snippet=snippet))
            if len(results) >= limit:
                break
        return results

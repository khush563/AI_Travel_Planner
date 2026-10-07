import logging
from typing import Protocol

import httpx

from app.api.schemas import SearchHit

logger = logging.getLogger(__name__)


class WebSearch(Protocol):
    def search(self, query: str, limit: int = 6) -> list[SearchHit]: ...


class SerperSearch:
    """Live Google results through Serper's search API."""

    def __init__(self, api_key: str, client: httpx.Client | None = None):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=15)

    def search(self, query: str, limit: int = 6) -> list[SearchHit]:
        if not self.api_key:
            raise RuntimeError("SERPER_API_KEY is required")
        logger.info("web_search query_length=%d limit=%d", len(query), limit)
        response = self.client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            json={"q": query, "num": limit},
        )
        response.raise_for_status()
        return [
            SearchHit(title=row.get("title", ""), url=row["link"], snippet=row.get("snippet", ""))
            for row in response.json().get("organic", [])[:limit]
            if row.get("link")
        ]


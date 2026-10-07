from typing import Protocol

from app.api.schemas import SearchHit


class RestaurantRecommender(Protocol):
    def recommend(self, candidates: list[SearchHit], interests: list[str], budget_per_day: float) -> list[SearchHit]: ...


class SearchResultRecommender:
    """Ranks sourced dining/experience candidates without inventing venues."""

    def recommend(self, candidates: list[SearchHit], interests: list[str], budget_per_day: float) -> list[SearchHit]:
        terms = {term.casefold() for term in interests}
        terms.add("budget" if budget_per_day < 100 else "restaurant")
        return sorted(
            candidates,
            key=lambda item: sum(term in (item.title + " " + item.snippet).casefold() for term in terms),
            reverse=True,
        )[:5]


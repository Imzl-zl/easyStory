from __future__ import annotations

from .review_query_service import ReviewQueryService


def create_review_query_service() -> ReviewQueryService:
    return ReviewQueryService()

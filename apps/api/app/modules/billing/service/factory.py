from __future__ import annotations

from datetime import datetime
from typing import Callable

from app.shared.runtime import ModelPricing

from .billing_query_service import BillingQueryService
from .billing_service import BillingService


def create_billing_service(
    *,
    model_pricing: ModelPricing | None = None,
) -> BillingService:
    return BillingService(model_pricing=model_pricing or ModelPricing())


def create_billing_query_service(
    *,
    now_factory: Callable[[], datetime] | None = None,
) -> BillingQueryService:
    return BillingQueryService(now_factory=now_factory)

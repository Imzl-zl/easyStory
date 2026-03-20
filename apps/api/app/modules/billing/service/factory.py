from __future__ import annotations

from app.shared.runtime import ModelPricing

from .billing_service import BillingService


def create_billing_service(
    *,
    model_pricing: ModelPricing | None = None,
) -> BillingService:
    return BillingService(model_pricing=model_pricing or ModelPricing())

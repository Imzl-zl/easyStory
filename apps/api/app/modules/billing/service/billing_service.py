from __future__ import annotations

from datetime import datetime
from typing import Callable
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.service.dto import (
    BudgetCheckResultDTO,
    UsageType,
)
from app.modules.config_registry.schemas.config_schemas import BudgetConfig
from app.shared.runtime import ModelPricing

from .billing_query_support import utc_now
from .billing_service_support import (
    build_budget_statuses,
    create_token_usage,
    normalize_usage_tokens,
    validate_budget_config,
)


class BillingService:
    def __init__(
        self,
        *,
        model_pricing: ModelPricing,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.model_pricing = model_pricing
        self.now_factory = now_factory or utc_now

    async def record_usage_and_check_budget(
        self,
        db: AsyncSession,
        *,
        workflow_execution_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        node_execution_id: uuid.UUID | None,
        credential_id: uuid.UUID,
        usage_type: UsageType,
        model_name: str,
        input_tokens: int | None,
        output_tokens: int | None,
        budget_config: BudgetConfig,
    ) -> BudgetCheckResultDTO:
        recorded_at = self.now_factory()
        validate_budget_config(budget_config)
        normalized_input, normalized_output = normalize_usage_tokens(
            usage_type=usage_type,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        usage = await create_token_usage(
            db,
            project_id=project_id,
            node_execution_id=node_execution_id,
            credential_id=credential_id,
            usage_type=usage_type,
            model_name=model_name,
            input_tokens=normalized_input,
            output_tokens=normalized_output,
            recorded_at=recorded_at,
            model_pricing=self.model_pricing,
        )
        statuses = await build_budget_statuses(
            db,
            workflow_execution_id=workflow_execution_id,
            project_id=project_id,
            user_id=user_id,
            node_execution_id=node_execution_id,
            budget_config=budget_config,
            recorded_at=recorded_at,
        )
        return BudgetCheckResultDTO(
            usage=usage,
            statuses=statuses,
            exceeded_status=next((status for status in statuses if status.exceeded), None),
        )

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.billing.service import (
    BillingQueryService,
    TokenUsageViewDTO,
    WorkflowBillingSummaryDTO,
    create_billing_query_service,
)
from app.modules.billing.service.dto import UsageType
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_db_session

router = APIRouter(tags=["billing"])


def get_billing_query_service() -> BillingQueryService:
    return create_billing_query_service()


@router.get(
    "/api/v1/workflows/{workflow_id}/billing/summary",
    response_model=WorkflowBillingSummaryDTO,
)
def get_workflow_billing_summary(
    workflow_id: uuid.UUID,
    billing_query_service: BillingQueryService = Depends(get_billing_query_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkflowBillingSummaryDTO:
    return billing_query_service.get_workflow_summary(
        db,
        workflow_id,
        owner_id=current_user.id,
    )


@router.get(
    "/api/v1/workflows/{workflow_id}/billing/token-usages",
    response_model=list[TokenUsageViewDTO],
)
def list_workflow_token_usages(
    workflow_id: uuid.UUID,
    usage_type: UsageType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    billing_query_service: BillingQueryService = Depends(get_billing_query_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[TokenUsageViewDTO]:
    return billing_query_service.list_workflow_token_usages(
        db,
        workflow_id,
        owner_id=current_user.id,
        usage_type=usage_type,
        limit=limit,
    )

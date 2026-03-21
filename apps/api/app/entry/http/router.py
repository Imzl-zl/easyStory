from fastapi import APIRouter

from app.modules.analysis.entry.http.router import router as analysis_router
from app.modules.billing.entry.http.router import router as billing_router
from app.modules.context.entry.http.router import router as context_router
from app.modules.credential.entry.http.router import router as credential_router
from app.modules.content.entry.http.router import router as content_router
from app.modules.export.entry.http.router import router as export_router
from app.modules.observability.entry.http.router import router as observability_router
from app.modules.project.entry.http.router import router as project_router
from app.modules.review.entry.http.router import router as review_router
from app.modules.system.entry.http.router import router as system_router
from app.modules.template.entry.http.router import router as template_router
from app.modules.user.entry.http.router import router as auth_router
from app.modules.workflow.entry.http.router import router as workflow_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(credential_router)
api_router.include_router(project_router)
api_router.include_router(analysis_router)
api_router.include_router(content_router)
api_router.include_router(workflow_router)
api_router.include_router(context_router)
api_router.include_router(billing_router)
api_router.include_router(export_router)
api_router.include_router(review_router)
api_router.include_router(observability_router)
api_router.include_router(template_router)
api_router.include_router(system_router)

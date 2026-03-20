from fastapi import APIRouter

from app.modules.credential.entry.http.router import router as credential_router
from app.modules.content.entry.http.router import router as content_router
from app.modules.project.entry.http.router import router as project_router
from app.modules.system.entry.http.router import router as system_router
from app.modules.user.entry.http.router import router as auth_router
from app.modules.workflow.entry.http.router import router as workflow_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(credential_router)
api_router.include_router(project_router)
api_router.include_router(content_router)
api_router.include_router(workflow_router)
api_router.include_router(system_router)

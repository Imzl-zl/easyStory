from fastapi import APIRouter

from app.modules.content.entry.http.router import router as content_router
from app.modules.project.entry.http.router import router as project_router
from app.modules.system.entry.http.router import router as system_router

api_router = APIRouter()
api_router.include_router(project_router)
api_router.include_router(content_router)
api_router.include_router(system_router)

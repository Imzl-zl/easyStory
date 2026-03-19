from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/healthz", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

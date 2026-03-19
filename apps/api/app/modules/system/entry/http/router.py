from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

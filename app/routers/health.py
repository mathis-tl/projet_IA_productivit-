from fastapi import APIRouter

router = APIRouter()

@router.get("/z")
def healthz():
    # Check si l'API est up
    return {"status": "ok"}

"""Statistics router placeholder."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/", summary="Statistics placeholder")
async def get_stats() -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Stats endpoints not implemented")

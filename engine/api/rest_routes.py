from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = datetime.now(timezone.utc)


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()

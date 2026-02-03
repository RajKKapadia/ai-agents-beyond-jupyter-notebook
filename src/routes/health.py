from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthCheckResponse(BaseModel):
    status: str
    message: str


@router.get("/")
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint to verify the API is running.
    """
    return HealthCheckResponse(
        status="healthy",
        message="Service is up and running"
    )

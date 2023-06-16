from fastapi import APIRouter, status

from app.config.database import get_beanie_database
from app.models.responses import ShortResponse

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_description="HTTP server is OK",
    response_model=ShortResponse,
    description="Simple HTTP server health check.",
)
async def http_health_check():
    return ShortResponse(message="OK")


@router.get(
    "/db",
    status_code=status.HTTP_200_OK,
    response_description="DB connection is OK",
    response_model=ShortResponse,
    description="Checks if the DB is responsive.",
)
async def db_health_check():
    result = await get_beanie_database().command("dbstats")
    if result["ok"] != 1.0:
        raise RuntimeError(
            f"Mongo returned OK={result['ok']} status for 'dbstats'"
        )

    return ShortResponse(message="OK")

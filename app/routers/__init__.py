from fastapi import APIRouter

from app.config.logging import LoggerValueError, get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)

if (version := get_settings().API_VERSION) == "v1":
    from app.routers.v1.audios import router as audios_router
    from app.routers.v1.auth import router as auth_router
    from app.routers.v1.blocks import router as blocks_router
    from app.routers.v1.items import router as items_router
    from app.routers.v1.users import router as users_router
    from app.routers.v1.voices import router as voices_router
else:
    raise LoggerValueError(logger, f"API version {version} is not available.")

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(voices_router, tags=["languages and voices"])
router.include_router(items_router, prefix="/items", tags=["items"])
router.include_router(blocks_router, prefix="/items/{id}/blocks", tags=["blocks"])
router.include_router(audios_router, prefix="/items/{id}/audios", tags=["audios"])

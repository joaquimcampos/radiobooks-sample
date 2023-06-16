"""Expose logger and environment variables."""
from functools import cache

from pydantic import BaseSettings, root_validator

from app.config.logging import LoggerValueError, get_logger

logger = get_logger(__name__)


class DidWeRaise:
    """Context manager to see if exception was raised once in `finally`."""
    __slots__ = ('exception_happened', )  # instances will take less memory

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # If no exception happened the `exc_type` is None
        self.exception_happened = exc_type is not None


class Settings(BaseSettings):
    """
    BaseSettings, from Pydantic, validates the data so that when we create an instance
    of Settings, environment and testing will have types of str and bool, respectively.
    Parameters:
    Returns:
        instance of Settings
    """
    MONGO_URL: str
    MONGO_DB: str = ""
    TEST_MONGO_DB: str = ""
    LOCAL: int = 0  # whether to save files locally and not upload to aws
    APP_VERSION: str = "0.0.1-dev"
    API_VERSION: str = "v1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_REGION_NAME: str = ""

    @root_validator
    def env_var_exists(cls, values: dict[str, str]) -> dict[str, str]:
        if not (values["MONGO_DB"] or values["TEST_MONGO_DB"]):
            raise LoggerValueError(
                logger, 'Need to provide either "MONGO_DB" or "TEST_MONGO_DB" env vars.'
            )
        if not values["LOCAL"]:
            if not values["AWS_ACCESS_KEY_ID"]:
                raise LoggerValueError(
                    logger, 'Need to provide "AWS_ACCESS_KEY_ID"'
                )
            if not values["AWS_SECRET_ACCESS_KEY"]:
                raise LoggerValueError(
                    logger, 'Need to provide "AWS_SECRET_ACCESS_KEY"'
                )
            if not values["AWS_S3_BUCKET"]:
                raise LoggerValueError(
                    logger, 'Need to provide "AWS_S3_BUCKET"'
                )
            if not values["AWS_REGION_NAME"]:
                raise LoggerValueError(
                    logger, 'Need to provide "AWS_REGION_NAME"'
                )

        return values

    class Config:
        case_sensitive = True
        orm_mode = True


@cache
def get_settings():
    logger.info("Loading config settings from the environment...")
    return Settings()

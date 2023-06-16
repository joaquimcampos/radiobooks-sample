from beanie import init_beanie
from bunnet import init_bunnet
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.database import Database
from starlette.datastructures import State

from app.config.settings import get_settings
from app.models.blocks import Block, BunnetBlock
from app.models.collections import Collections
from app.models.items import BunnetItem, Item
from app.models.spans import BunnetSpan, Span  # TODO: Remove
from app.models.users import UserInDB

# stores database states
_APP_GLOBAL_STATE: State | None = None


async def async_init_beanie_database(
    app_global_state: State,
    mongo_url: str = "",
    database_name: str = "",
) -> None:
    settings = get_settings()
    mongo_url = mongo_url or settings.MONGO_URL
    database_name = database_name or settings.MONGO_DB

    beanie_client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_url)
    beanie_database: AsyncIOMotorDatabase = beanie_client[database_name]

    global _APP_GLOBAL_STATE
    _APP_GLOBAL_STATE = app_global_state

    _APP_GLOBAL_STATE.beanie_client = beanie_client
    _APP_GLOBAL_STATE.beanie_database = beanie_database

    await init_beanie(
        database=beanie_database,
        document_models=[UserInDB, Item, Block, Span]  # type: ignore
    )


def init_bunnet_database(
    app_global_state: State,
    mongo_url: str = "",
    database_name: str = "",
) -> None:
    settings = get_settings()
    mongo_url = mongo_url or settings.MONGO_URL
    database_name = database_name or settings.MONGO_DB

    global _APP_GLOBAL_STATE
    _APP_GLOBAL_STATE = app_global_state
    bunnet_client: MongoClient = MongoClient(mongo_url)
    bunnet_database: Database = bunnet_client[database_name]

    _APP_GLOBAL_STATE.bunnet_client = bunnet_client
    _APP_GLOBAL_STATE.bunnet_database = bunnet_database

    init_bunnet(
        database=bunnet_database,
        document_models=[BunnetItem, BunnetBlock, BunnetSpan]  # type: ignore
    )


async def async_init_databases(
    app_global_state: State,
    mongo_url: str = "",
    database_name: str = ""
) -> None:
    await async_init_beanie_database(app_global_state, mongo_url, database_name)
    init_bunnet_database(app_global_state, mongo_url, database_name)


def get_beanie_database() -> AsyncIOMotorDatabase:
    if _APP_GLOBAL_STATE is None:
        raise RuntimeWarning("DB not initialized with a global state.")

    return _APP_GLOBAL_STATE.beanie_database


async def async_drop_collections() -> None:
    beanie_db = get_beanie_database()
    for collection in Collections:
        await beanie_db.drop_collection(collection.value)

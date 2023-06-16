from beanie.odm.fields import PydanticObjectId
from beanie.odm.operators.find.comparison import In

from app.auth.password import get_password_hash
from app.config.logging import LoggerOSError, get_logger
from app.config.settings import get_settings
from app.models.base import IdModel
from app.models.blocks import Block
from app.models.items import BasicItem, Item
from app.models.spans import Span
from app.models.users import BasicUser, UserInDB
from app.utils.aws import async_delete_s3_user  # type: ignore

logger = get_logger(__name__)


########
# GET
async def async_get_user_db(username: str) -> UserInDB | None:
    user_db = await UserInDB.find_one(UserInDB.username == username)
    if user_db:
        return user_db

    return None


########
# ADD
async def async_add_user_db(
    username: str,
    password: str,
    raise_if_exists: bool = True
) -> None:
    user = await UserInDB.find_one({"username": username}).project(BasicUser)
    if user and raise_if_exists:
        raise LoggerOSError(logger, "User already exists in DB.")

    hashed_password = get_password_hash(password)
    new_user = UserInDB(
        id=PydanticObjectId(),
        username=username,
        hashed_password=hashed_password
    )
    await new_user.insert()


########
# LIST
async def async_list_users_db() -> list[UserInDB]:
    users = await UserInDB.all().to_list()
    return users


async def async_list_user_items_db(user_id: PydanticObjectId) -> list[BasicItem]:
    return await Item.find({"owner_id": user_id}).project(BasicItem).to_list()


########
# DELETE

async def async_delete_user_db_s3(username: str) -> bool:
    user_db = await async_get_user_db(username)
    if not user_db:
        return False

    # Find user item ids
    id_models = await Item.find({"owner_id": user_db.id}).project(IdModel).to_list()
    item_ids = [id_model.id for id_model in id_models]

    # Find all blocks for all user items
    id_models = await Block.find(In("item_id", item_ids)).project(IdModel).to_list()
    block_ids = [id_model.id for id_model in id_models]

    await Span.find(In("block_id", block_ids)).delete()  # delete all user spans
    await Block.find(In("item_id", item_ids)).delete()  # delete all user blocks
    await Item.find(In("_id", item_ids)).delete()  # delete all user items

    if not get_settings().LOCAL:
        await async_delete_s3_user(user_db.id)  # delete all user-related stuff from s3

    delete_result = await user_db.delete()  # delete user
    if (delete_result is None or delete_result.deleted_count == 0):
        return False

    return True

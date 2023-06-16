import os
from functools import cache

from beanie.odm.fields import PydanticObjectId
from s3transfer.futures import TransferFuture

from app.config.aws import get_async_s3_session, get_s3_client, get_s3_transfer
from app.config.logging import get_logger

logger = get_logger(__name__)


###########
# Transfers

def write_stream_to_s3(contents: bytes, s3_key: str) -> None:
    get_s3_client().write_stream_to_s3(contents, s3_key)


def get_s3_num_workers() -> int:
    return get_s3_client().num_workers


def append_to_s3_futures(
    futures: list[TransferFuture],
    filename: str,
    s3_key: str
) -> None:
    future = get_s3_transfer().get_s3_future(filename, s3_key)
    futures.append(future)


def shutdown_s3_transfer() -> None:
    get_s3_transfer().shutdown


def delete_s3_obj(key: str) -> None:
    get_s3_client().delete_s3_obj(key)


########
# DELETE
async def async_delete_s3_objs_in_prefix(prefix: str) -> None:
    await get_async_s3_session().async_delete_objs_in_prefix(prefix)


def delete_s3_objs_in_prefix(prefix: str) -> None:
    get_s3_client().delete_s3_objs_in_prefix(prefix)


################
# items
def get_user_path(user_id: PydanticObjectId) -> str:
    return f'some_path_for_user_{user_id}'


@cache
def get_item_path(user_id: PydanticObjectId, item_id: PydanticObjectId) -> str:
    return f'some_path_for_user_{user_id}_item_{item_id}'


def get_s3_item_obj_key(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId,
    filename: str
) -> str:
    item_path = get_item_path(user_id, item_id)
    return os.path.join(item_path, filename)


########
# audios

def get_item_audio_prefix(user_id: PydanticObjectId, item_id: PydanticObjectId) -> str:
    item_path = get_item_path(user_id, item_id)
    return os.path.join(item_path, "some audio path")


def get_block_audio_s3_prefix(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId,
    block_id: PydanticObjectId
) -> str:
    audio_prefix = get_item_audio_prefix(user_id, item_id)
    return os.path.join(audio_prefix, str(block_id))


def get_block_audio_s3_key(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId,
    block_id: PydanticObjectId,
    filename: str
) -> str:
    block_prefix = get_block_audio_s3_prefix(user_id, item_id, block_id)
    return os.path.join(block_prefix, f'{filename}.wav')


########
# info
def get_language_samples_prefix(language_name: str) -> str:
    return os.path.join("some samples path", language_name)


########
# delete
async def async_delete_s3_item(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId
) -> None:
    item_path = get_item_path(user_id, item_id)
    await async_delete_s3_objs_in_prefix(item_path)


def delete_s3_item(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId
) -> None:
    item_path = get_item_path(user_id, item_id)
    delete_s3_objs_in_prefix(prefix=item_path)

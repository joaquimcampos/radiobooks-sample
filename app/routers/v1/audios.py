from typing import Annotated

from beanie.odm.fields import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.auth.users import get_current_active_basic_user
from app.crud.audios import (  # type: ignore
    async_delete_item_block_audio_db_s3, async_delete_item_block_audio_s3,
    async_set_item_block_batch_audio_in_progress, process_item_block_audio,
)
from app.crud.blocks import (
    async_get_item_block_audio, async_get_item_block_batch_read_block_ids,
    async_get_item_block_db, async_list_item_block_audios_db,
)
from app.crud.items import (  # type: ignore
    async_get_block_batch_ids_from_block_id_range, async_get_user_id_model_item_db,
    async_get_user_item_db, process_item_read_block_batch_audio,
)
from app.models.blocks import BlockAudio, BlockIdListIn, BlockIdRange
from app.models.fields import AudioStatus, Bodies, Queries
from app.models.responses import ShortResponse
from app.models.users import BasicUser
from app.routers.http_exceptions import (
    BadGatewayHTTPException, BadRequestHTTPException, InternalServerErrorHTTPException,
    NotFoundHTTPException, UnauthorizedHTTPException,
)

router = APIRouter()


@router.post(
    "/{block_id}",
    status_code=status.HTTP_202_ACCEPTED,
    description="Request audio for block :{block_id}:.",
    response_model=ShortResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: BadRequestHTTPException.response,
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response,
    }
)
async def request_block_audio(
    background_tasks: BackgroundTasks,
    id: PydanticObjectId,
    block_id: PydanticObjectId,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    # can raise HTTP_400_BAD_REQUEST
    item_db = await async_get_user_item_db(user.id, id)
    if not item_db:
        raise NotFoundHTTPException(f"item :{id}: not found.")

    block_db = await async_get_item_block_db(item_db.id, block_id)
    if not block_db:
        raise NotFoundHTTPException(f"Block :{block_id}: not found.")
    elif block_db.read is False:
        raise BadRequestHTTPException(
            f"block :{block_id}: has :read:=False. "
            "Set :read: to True before requesting audio."
        )

    await async_delete_item_block_audio_s3(item_db.owner_id, item_db.id, block_db.id)
    await block_db.set({
        "audio_status": AudioStatus.IN_PROGRESS,
        "audio_path": None
    })
    background_tasks.add_task(process_item_block_audio, item_db, block_db)

    return ShortResponse(message="OK")


@router.get(
    "/{block_id}",
    status_code=status.HTTP_200_OK,
    response_description="A :BlockAudio: model",
    response_model=BlockAudio,
    response_model_exclude_none=True,
    responses={
        status.HTTP_400_BAD_REQUEST: BadRequestHTTPException.response,
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response
    }
)
async def get_block_audio(
    id: PydanticObjectId,
    block_id: PydanticObjectId,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    # can raise HTTP_400_BAD_REQUEST
    item = await async_get_user_id_model_item_db(user.id, id)  # IdModel
    if not item:
        raise NotFoundHTTPException(f"item :{id}: not found.")

    block_audio = await async_get_item_block_audio(item.id, block_id)
    if not block_audio:
        raise NotFoundHTTPException(f"Block :{block_id}: not found.")

    return block_audio


@router.delete(
    "/{block_id}",
    status_code=status.HTTP_200_OK,
    description="Delete block audio from db and s3 for block :{block_id}:.",
    response_model=ShortResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response
    }
)
async def delete_block_audio(
    id: PydanticObjectId,
    block_id: PydanticObjectId,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    # can raise HTTP_400_BAD_REQUEST
    item = await async_get_user_id_model_item_db(user.id, id)  # IdModel
    if not item:
        raise NotFoundHTTPException(f"item :{id}: not found.")

    deleted = await async_delete_item_block_audio_db_s3(user.id, item.id, block_id)
    if not deleted:
        raise NotFoundHTTPException(f"block :{block_id}: not found.")

    return ShortResponse(message="OK")


@router.post(
    "/",
    status_code=status.HTTP_202_ACCEPTED,
    description=(
        "Request audios for blocks. <br>"
        "Exactly one of the following body models should be given: <br>"
        "1. :BlockIdListIn: <br>"
        "2: :BlockIdRange:"
    ),
    response_model=ShortResponse,
    response_model_exclude_none=True,
    responses={
        status.HTTP_400_BAD_REQUEST: BadRequestHTTPException.response,
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response,
        status.HTTP_500_INTERNAL_SERVER_ERROR:
            InternalServerErrorHTTPException.response,
        status.HTTP_502_BAD_GATEWAY: BadGatewayHTTPException.response
    }
)
# https://fastapi.tiangolo.com/tutorial/schema-extra-example/
async def request_block_batch_audio(
    background_tasks: BackgroundTasks,
    id: PydanticObjectId,
    block_ids: Annotated[
        BlockIdListIn | BlockIdRange | None,
        Bodies.block_ids_list_or_range
    ] = None,
    only_missing: Annotated[bool, Queries.only_missing_audio_flag] = False,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    # Can raise HTTP_400_BAD_REQUEST
    item_db = await async_get_user_item_db(user.id, id)
    if not item_db:
        raise NotFoundHTTPException(f"item :{id}: not found.")

    block_ids_: list[PydanticObjectId] | None = None  # default
    if isinstance(block_ids, BlockIdListIn):
        block_ids_ = block_ids.block_ids
    elif isinstance(block_ids, BlockIdRange):
        # Can raise HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
        block_ids_ = await async_get_block_batch_ids_from_block_id_range(
            item_db.id,
            start_id=block_ids.start_id,
            end_id=block_ids.end_id
        )

    # Can raise HTTP_502_BAD_GATEWAY
    read_block_ids = await async_get_item_block_batch_read_block_ids(
        item_db.id, block_ids=block_ids_, only_missing=only_missing
    )
    if not read_block_ids:
        raise BadRequestHTTPException(
            "No blocks with :read:=True in request. "
            "Set :read:=True in some block before requesting audio."
        )
    # Can raise HTTP_502_BAD_GATEWAY
    await async_set_item_block_batch_audio_in_progress(item_db, read_block_ids)
    background_tasks.add_task(
        process_item_read_block_batch_audio, item_db, read_block_ids
    )

    return ShortResponse(message="OK")


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    description="Get list of audio tasks for item :{id}:.",
    response_description="A list of :BasicAudioTask: models",
    response_model=list[BlockAudio],
    response_model_exclude_none=True,
    responses={
        status.HTTP_400_BAD_REQUEST: BadRequestHTTPException.response,
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response
    }
)
async def list_item_block_audios(
    id: PydanticObjectId,
    block_ids: Annotated[
        BlockIdListIn | BlockIdRange | None,
        Bodies.block_ids_list_or_range
    ] = None,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    # can raise HTTP_400_BAD_REQUEST
    item = await async_get_user_id_model_item_db(user.id, id)  # IdModel
    if not item:
        raise NotFoundHTTPException(f'item with it :{id}: not found.')

    block_ids_: list[PydanticObjectId] | None = None  # default
    if isinstance(block_ids, BlockIdListIn):
        block_ids_ = block_ids.block_ids
    elif isinstance(block_ids, BlockIdRange):
        # type(block_ids) == BlockIdRange
        # Can raise HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
        block_ids_ = await async_get_block_batch_ids_from_block_id_range(
            item.id,
            start_id=block_ids.start_id,
            end_id=block_ids.end_id,
        )

    return await async_list_item_block_audios_db(item.id, block_ids=block_ids_)

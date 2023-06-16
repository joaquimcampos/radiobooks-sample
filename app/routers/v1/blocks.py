from typing import Annotated

from beanie.odm.fields import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.auth.users import get_current_active_basic_user
from app.crud.audios import get_audios_for_item_blocks  # type: ignore
from app.crud.blocks import (  # type: ignore
    async_add_item_block_db, async_delete_item_block_db_s3,
    async_get_block_out_from_block_db, async_get_item_block_db,
    async_get_item_block_out_db, async_replace_item_block_db_s3,
)
from app.crud.items import async_get_user_id_model_item_db, async_get_user_item_db
from app.models.blocks import BlockIn, BlockInPrevId, BlockOut
from app.models.fields import AudioStatus, Bodies, Queries
from app.models.responses import ShortResponse
from app.models.users import BasicUser
from app.routers.http_exceptions import (
    BadGatewayHTTPException, BadRequestHTTPException, InternalServerErrorHTTPException,
    NotFoundHTTPException, UnauthorizedHTTPException,
)

router = APIRouter()


@router.get(
    "/{block_id}",
    status_code=status.HTTP_200_OK,
    response_description="A :BlockOut: model",
    response_model=BlockOut,
    response_model_exclude_none=True,
    responses={
        status.HTTP_400_BAD_REQUEST: BadRequestHTTPException.response,
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response,
        status.HTTP_500_INTERNAL_SERVER_ERROR:
            InternalServerErrorHTTPException.response
    }
)
async def get_block(
    id: PydanticObjectId,
    block_id: PydanticObjectId,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    # can raise HTTP_400_BAD_REQUEST
    item = await async_get_user_id_model_item_db(user.id, id)  # IdModel
    if not item:
        raise NotFoundHTTPException(f"item {id}: not found.")

    # Can raise HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
    block_out = await async_get_item_block_out_db(item.id, block_id)  # BlockOut
    if not block_out:
        raise NotFoundHTTPException(f"block {block_id}: not found.")

    return block_out


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    description="Add new block with :read:=True after block :{prev_block_id}:.",
    response_description="A :BlockOut: Model",
    response_model=BlockOut,
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
async def create_new_block(
    background_tasks: BackgroundTasks,
    id: PydanticObjectId,
    prev_block_id_and_block: Annotated[BlockInPrevId, Bodies.prev_block_id_and_block],
    get_audio: Annotated[bool, Queries.audio_flag] = False,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    prev_block_id = prev_block_id_and_block.prev_block_id
    block_in = prev_block_id_and_block.block
    # Can raise HTTP_400_BAD_REQUEST
    item_db = await async_get_user_item_db(user.id, id)
    if not item_db:
        raise NotFoundHTTPException(f"item {id}: not found.")

    # Can raise HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_502_BAD_GATEWAY
    block_db = await async_add_item_block_db(item_db.id, block_in, prev_block_id)
    # Can raise HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
    block_out = await async_get_block_out_from_block_db(block_db)

    if get_audio:
        await block_db.set({"audio_status": AudioStatus.IN_PROGRESS})
        background_tasks.add_task(get_audios_for_item_blocks, item_db, [block_out])

    return block_out


@router.put(
    "/{block_id}",
    status_code=status.HTTP_200_OK,
    description="Modify block :{block_id}:. Only accepts blocks with :read:=True.",
    response_description="A :BlockOut: Model",
    response_model=BlockOut,
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
async def update_block(
    background_tasks: BackgroundTasks,
    id: PydanticObjectId,
    block_id: PydanticObjectId,
    block: Annotated[BlockIn, Bodies.block_in],
    get_audio: Annotated[bool, Queries.audio_flag] = False,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    # can raise HTTP_400_BAD_REQUEST
    item_db = await async_get_user_item_db(user.id, id)
    if not item_db:
        raise NotFoundHTTPException(f"item {id}: not found.")

    old_block_db = await async_get_item_block_db(item_db.id, block_id)  # Block
    if not old_block_db:
        raise NotFoundHTTPException(f"block :{block_id}: not found.")
    elif old_block_db.read is False:
        raise BadRequestHTTPException(
            f"block :{block_id}: has :read:=False. Set :read:=True before modifying."
        )

    block_db = await async_replace_item_block_db_s3(  # Can raise HTTP_502_BAD_GATEWAY
        user.id, item_db.id, old_block_db, block
    )
    # Can raise HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
    block_out = await async_get_block_out_from_block_db(block_db)

    if get_audio:
        await block_db.set({
            "audio_status": AudioStatus.IN_PROGRESS, "audio_path": None
        })
        background_tasks.add_task(get_audios_for_item_blocks, item_db, [block_out])

    return block_out


@router.delete(
    "/{block_id}",
    status_code=status.HTTP_200_OK,
    description="Delete block {block_id}:, including audio from db and s3.",
    response_model=ShortResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response
    }
)
async def delete_block(
    id: PydanticObjectId,
    block_id: PydanticObjectId,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    # can raise HTTP_400_BAD_REQUEST
    item = await async_get_user_id_model_item_db(user.id, id)  # IdModel
    if not item:
        raise NotFoundHTTPException(f"item {id}: not found.")

    if not await async_delete_item_block_db_s3(user.id, item.id, block_id):
        raise NotFoundHTTPException(f"block {block_id}: not found.")

    return ShortResponse(message="OK")

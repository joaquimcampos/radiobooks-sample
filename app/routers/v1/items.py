from typing import Annotated

from beanie.odm.fields import PydanticObjectId
from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile, status,
)
from pydantic import Json, NonNegativeInt, PositiveInt

from app.auth.users import get_current_active_basic_user
from app.config.variables import Routers as VarConfig  # type: ignore
from app.crud.items import (  # type: ignore
    async_add_basic_item_db, async_delete_user_item_db_s3,
    async_get_item_out_from_item_db, async_get_user_basic_item_db,
    async_get_user_item_db, process_item_audios, upload_cover_and_document,
)
from app.crud.users import async_list_user_items_db
from app.models.fields import AudioOptions, Queries
from app.models.items import BasicItem, CoverInfo, ItemIn, ItemOut
from app.models.responses import ShortResponse
from app.models.users import BasicUser
from app.routers.http_exceptions import (
    BadGatewayHTTPException, BadRequestHTTPException, InternalServerErrorHTTPException,
    NotFoundHTTPException, UnauthorizedHTTPException, UnsupportedMediaTypeHTTPException,
)
from app.utils.aws import get_default_cover_s3_key  # type: ignore
from app.utils.files import verify_image_file, verify_item_file
from app.utils.items import verify_voice_info  # type: ignore

router = APIRouter()


#################################################################
# Get, List, Delete Item


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_description="A list of :BasicItem: models",
    response_model=list[BasicItem],
    response_model_exclude_none=True,
    responses={
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response
    }
)
async def list_items(user: BasicUser = Depends(get_current_active_basic_user)):
    return await async_list_user_items_db(user.id)


@router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    response_description="A :BasicItem: model",
    response_model=BasicItem,
    response_model_exclude_none=True,
    responses={
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response
    }
)
async def get_item(
    id: PydanticObjectId,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    item = await async_get_user_basic_item_db(user.id, id)
    if not item:
        raise NotFoundHTTPException(f"item {id}: not found.")

    return item


@router.get(
    "/{id}/document",
    status_code=status.HTTP_200_OK,
    response_description="An :ItemOut: model",
    response_model=ItemOut,
    response_model_exclude_none=True,
    responses={
        status.HTTP_400_BAD_REQUEST: BadRequestHTTPException.response,
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response,
        status.HTTP_500_INTERNAL_SERVER_ERROR:
            InternalServerErrorHTTPException.response
    }
)
async def get_item_document(
    background_tasks: BackgroundTasks,
    id: PydanticObjectId,
    response: Response,
    start_page: Annotated[NonNegativeInt | None, Queries.start_page] = None,
    end_page: Annotated[PositiveInt | None, Queries.end_page] = None,
    get_audios: Annotated[AudioOptions | None, Queries.audio_options] = None,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    if ((start_page is not None) and
            (end_page is not None) and
            (start_page >= end_page)):
        BadRequestHTTPException(":start_page: should be smaller than :end_page:")

    # can raise HTTP_400_BAD_REQUEST
    item_db = await async_get_user_item_db(user.id, id)
    if not item_db:
        raise NotFoundHTTPException(f"item {id}: not found.")

    # can raise HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
    item_out = await async_get_item_out_from_item_db(
        item_db,
        start_page=start_page,
        end_page=end_page
    )

    # Add full content length header
    # https://fastapi.tiangolo.com/advanced/response-headers/
    # https://stackoverflow.com/questions/39047624/
    # is-there-an-easy-way-to-estimate-size-of-a-json-object
    response.headers[VarConfig.FULL_CONTENT_LENGTH_HEADER] = (
        str(len(item_out.json()))
    )
    if get_audios is not None:
        # Process blocks; generate audios for blocks with :read:=True
        # (and process blocks with missing audios if :audios: is :AudioOptions.missing:)
        background_tasks.add_task(
            process_item_audios,
            item_db,
            item_out,
            only_missing=(True if get_audios is AudioOptions.MISSING else False)
        )

    return item_out


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    response_model=ShortResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response
    }
)
async def delete_item(
    id: PydanticObjectId,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    if not await async_delete_user_item_db_s3(user.id, id):
        raise NotFoundHTTPException(f"item {id}: not found.")

    return ShortResponse(message="OK")


#################################################################
# Upload Item

@router.post(
    "/",
    status_code=status.HTTP_202_ACCEPTED,
    description=("Upload a PDF/Epub file, a cover image, and the basic item info. "
                 "Check status in :/items/{id}: endpoint."),
    response_description="A :BasicItem: model",
    response_model=BasicItem,
    response_model_exclude_none=True,
    responses={
        status.HTTP_400_BAD_REQUEST:
            BadRequestHTTPException.response,
        status.HTTP_401_UNAUTHORIZED:
            UnauthorizedHTTPException.response,
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
            UnsupportedMediaTypeHTTPException.response,
        status.HTTP_502_BAD_GATEWAY:
            BadGatewayHTTPException.response
    },
)
async def upload_item(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(description="PDF/Epub file"),
    cover: UploadFile | None = File(default=None, description="Item cover"),
    info: Json[ItemIn] = Form(description=":ItemIn: model"),
    page_limit: PositiveInt | None = None,
    user: BasicUser = Depends(get_current_active_basic_user)
):
    verify_voice_info(info)  # can raise HTTP_400_BAD_REQUEST
    verify_item_file(file)  # can raise HTTP_415_UNSUPPORTED_MEDIA_TYPE
    if cover is not None:
        verify_image_file(cover)  # can raise HTTP_415_UNSUPPORTED_MEDIA_TYPE

    item_id = PydanticObjectId()  # initialize new id
    # Can raise HTTP_502_BAD_GATEWAY
    item_db = await async_add_basic_item_db(user.id, item_id, info)
    background_tasks.add_task(
        upload_cover_and_document,
        user.id, item_id, file, info, cover=cover, page_limit=page_limit
    )

    return item_db


# https://fastapi.tiangolo.com/tutorial/dependencies/#__tabbed_1_1
@router.get(
    "/default-cover/",
    status_code=status.HTTP_200_OK,
    response_description="A :CoverInfo: model",
    response_model=CoverInfo,
    responses={
        status.HTTP_401_UNAUTHORIZED: UnauthorizedHTTPException.response,
        status.HTTP_404_NOT_FOUND: NotFoundHTTPException.response
    }
)
async def get_default_cover(_: BasicUser = Depends(get_current_active_basic_user)):
    return CoverInfo(cover_path=get_default_cover_s3_key())

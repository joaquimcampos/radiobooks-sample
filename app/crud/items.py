from typing import Any

from beanie.odm.fields import PydanticObjectId
from fastapi import UploadFile
from pydantic import NonNegativeInt, PositiveInt

from app.config.logging import LoggerOSError, LoggerValueError, get_logger
from app.config.settings import get_settings
from app.crud.blocks import (
    append_cur_block_to_blocks, async_get_item_block_page_nb,
    async_get_item_head_block_id, async_list_item_block_ids_db, construct_block_dict,
    get_cur_block, get_item_head_block_id, get_page_range_block_query_dict,
)
from app.models.base import IdModel
from app.models.blocks import BaseBlock, Block, BlockDict, BlockOut, BunnetBlock
from app.models.fields import DocStatus
from app.models.items import BasicItem, BunnetItem, Item, ItemIdDocStatus, ItemIn
from app.models.spans import BaseSpan, BunnetSpan, Span, SpanIdBlockId
from app.routers.http_exceptions import (
    BadGatewayHTTPException, BadRequestHTTPException, InternalServerErrorHTTPException,
    NotFoundHTTPException,
)
from app.utils.aws import async_delete_s3_item, get_default_cover_s3_key  # type: ignore
from app.utils.items import read_file_contents, upload_file  # type: ignore

logger = get_logger(__name__)


########
# GET

async def async_get_user_basic_item_db(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId
) -> BasicItem | None:
    """Does not require that item.status == DocStatus.COMPLETED."""
    item = await Item.find_one(
        {"_id": item_id, "owner_id": user_id}
    ).project(BasicItem)
    if item:
        return item

    return None


def check_status(item: Item | ItemIdDocStatus) -> None:
    if item.status != DocStatus.COMPLETED:
        raise BadRequestHTTPException(f'Item :{item.id}: is still not processed.')


async def async_get_user_id_model_item_db(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId
) -> IdModel | None:
    item = await Item.find_one(
        {"_id": item_id, "owner_id": user_id}
    ).project(ItemIdDocStatus)
    if item:
        check_status(item)
        return item

    return None


async def async_get_user_item_db(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId
) -> Item | None:
    """Retrieve item :item_id:."""
    item_db = await Item.find_one({"_id": item_id, "owner_id": user_id})
    if item_db:
        check_status(item_db)
        return item_db

    return None


##########
# Item out

###
async def async_get_item_block_dict(
    item_id: PydanticObjectId,
    start_page: NonNegativeInt | None = None,
    end_page: PositiveInt | None = None
) -> BlockDict:
    """Get dictionary with blocks, head_span_id, and spans."""
    block_query_dict = get_page_range_block_query_dict(
        item_id,
        start_page=start_page,
        end_page=end_page
    )
    blocks = await Block.find(block_query_dict).project(BaseBlock).to_list()

    # get all block head spans (_id and block_id)
    block_ids = [block.id for block in blocks]
    head_spans = await Span.find({
        "block_id": {"$in": block_ids},
        "is_head": True
    }).project(SpanIdBlockId).to_list()

    # get all item spans
    spans = await Span.find(
        {"block_id": {"$in": block_ids}}
    ).project(BaseSpan).to_list()

    try:
        block_dict = construct_block_dict(blocks, head_spans, spans)
    except (LoggerOSError, LoggerValueError) as exc:
        raise NotFoundHTTPException(exc.msg)

    return block_dict


def get_item_block_dict(item_id: PydanticObjectId) -> BlockDict:
    """Get dictionary with blocks, head_span_id, and spans."""
    # get all item blocks
    blocks = BunnetBlock.find({"item_id": item_id}).project(BaseBlock).to_list()

    # get all block head spans (_id and block_id)
    block_ids = [block.id for block in blocks]
    head_spans = BunnetSpan.find({
        "block_id": {"$in": block_ids},
        "is_head": True
    }).project(SpanIdBlockId).to_list()

    # get all item spans
    spans = BunnetSpan.find(
        {"block_id": {"$in": block_ids}}
    ).project(BaseSpan).to_list()

    return construct_block_dict(blocks, head_spans, spans)
###


###
# Blocks linked list construction
def aux_get_item_block_ids(
    block_dict: BlockDict,
    head_block_id: PydanticObjectId,
    end_id: PydanticObjectId | None = None
) -> list[PydanticObjectId]:
    """
    Auxiliary function to construct linked list of block ids.
    if :start_id: or :start_page: were given, head_block_id: isn't necessarily
    the item head block.
    """
    block_ids: list[PydanticObjectId] = []
    cur_block_id: PydanticObjectId | None = head_block_id
    while cur_block_id is not None:
        cur_block = get_cur_block(block_dict, cur_block_id)
        block_ids.append(cur_block.id)  # append to ids

        if ((end_id is not None) and (cur_block_id == end_id)):
            break  # end_id is still added to block_ids

        cur_block_id = cur_block.next_id

    if end_id is not None:
        if (block_ids[-1] != end_id):
            raise LoggerOSError(
                logger,
                f"Could not construct linked list from block :{head_block_id}: "
                f"to block :{end_id}:. Got end block :{block_ids[-1]}:."
            )

    return block_ids


def aux_get_item_blocks_out(
    block_dict: BlockDict,
    head_block_id: PydanticObjectId,
    end_page: PositiveInt | None = None
) -> list[BlockOut]:
    """
    Auxiliary function to construct list[BlockOut], common to both sync and async.
    if :start_id: or :start_page: were given, head_block_id: isn't necessarily
    the item head block.
    """
    blocks: list[BlockOut] = []
    cur_block_id: PydanticObjectId | None = head_block_id
    while cur_block_id is not None:
        cur_block = get_cur_block(block_dict, cur_block_id)
        if ((end_page is not None) and (cur_block.page_nb >= end_page)):
            break  # blocks in end_page are not added to blocks

        # can raise LoggerOSError
        append_cur_block_to_blocks(cur_block, blocks, block_dict)
        cur_block_id = cur_block.next_id

    return blocks


###
# Construct block linked lists
async def async_get_block_batch_ids_from_block_id_range(
    item_id: PydanticObjectId,
    start_id: PydanticObjectId | None = None,
    end_id: PydanticObjectId | None = None,
) -> list[PydanticObjectId]:
    """Construct list of block ids from linked list range."""
    end_page: PositiveInt | None = None
    if end_id is not None:
        end_block_page = await async_get_item_block_page_nb(item_id, end_id)
        if not end_block_page:
            raise NotFoundHTTPException("End block :{end_id}: not found.")
        end_page = end_block_page + 1  # end_page is excluded

    start_page: NonNegativeInt | None = None
    if start_id is not None:
        start_block_page = await async_get_item_block_page_nb(item_id, start_id)
        if not start_block_page:
            raise NotFoundHTTPException("Start block :{start_id}: not found.")
        start_page = start_block_page  # start page is included
        head_block_id = start_id
    else:
        # Can raise NotFoundException, InternalServerError
        aux_id = await async_get_item_head_block_id(
            item_id,
            start_page=None,
            end_page=end_page
        )
        if aux_id is None:
            return []  # if no blocks were found in :start_id:-:end_id: range

        head_block_id = aux_id

    block_dict = await async_get_item_block_dict(  # Can raise NotFoundException
        item_id,
        start_page=start_page,
        end_page=end_page
    )
    try:
        block_ids = aux_get_item_block_ids(
            block_dict,
            head_block_id,
            end_id=end_id,
        )
    except (LoggerOSError, LoggerValueError) as exc:
        raise InternalServerErrorHTTPException(exc.msg)

    return block_ids


async def async_get_item_blocks_out_db(
    item_id: PydanticObjectId,
    start_page: NonNegativeInt | None = None,
    end_page: PositiveInt | None = None
) -> list[BlockOut]:
    """Construct list[BlockOut] for item."""
    # Can raise NotFoundException, InternalServerError
    head_block_id = await async_get_item_head_block_id(
        item_id,
        start_page=start_page,
        end_page=end_page
    )
    if head_block_id is None:
        return []  # if no blocks were found in :page_range:

    # Can raise NotFoundException
    block_dict = await async_get_item_block_dict(
        item_id,
        start_page=start_page,
        end_page=end_page
    )
    try:
        blocks_out = aux_get_item_blocks_out(
            block_dict,
            head_block_id,
            end_page=end_page,
        )
    except (LoggerOSError, LoggerValueError) as exc:
        raise InternalServerErrorHTTPException(exc.msg)

    return blocks_out


def get_item_blocks_out_db(item_id: PydanticObjectId) -> list[BlockOut]:
    block_dict = get_item_block_dict(item_id)
    head_block_id = get_item_head_block_id(item_id)
    blocks_out = aux_get_item_blocks_out(block_dict, head_block_id)

    return blocks_out
###


########
# DELETE
async def async_delete_user_item_db_s3(
    user_id: PydanticObjectId,
    id: PydanticObjectId
) -> bool:
    item_db = await Item.find_one({"_id": id, "owner_id": user_id})
    if not item_db:
        return False

    block_ids = await async_list_item_block_ids_db(item_db.id)  # find item block ids
    await Span.find({"block_id": {"$in": block_ids}}).delete()  # delete all spans
    await Block.find({"item_id": item_db.id}).delete()  # delete all blocks

    if not get_settings().LOCAL:
        await async_delete_s3_item(user_id, item_db.id)  # delete item in s3

    delete_result = await item_db.delete()  # delete item
    if (delete_result is None or delete_result.deleted_count == 0):
        return False

    return True


########
# ADD

async def async_add_basic_item_db(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId,
    item_in: ItemIn
) -> Item:
    item = Item(
        id=item_id,
        owner_id=user_id,
        **item_in.dict()
    )
    logger.info(f'Inserting basic item :{item_id}: into DB.')
    item_db = await item.insert()
    if not item_db:
        raise BadGatewayHTTPException('Error in DB insertion of newly created item.')

    return item_db


########
# Upload

def update_item(
    item_id: PydanticObjectId,
    update_dict: dict[str, Any]
) -> None:
    for key in update_dict:
        if key not in BunnetItem.keys():
            raise LoggerValueError(logger, f"key :{key}: is not a field of Item.")

    update_query = BunnetItem.find_one(
        {"_id": item_id}
    ).update({"$set": update_dict}).run()

    if update_query.matched_count < 1:
        raise LoggerOSError(logger, f"Item :{item_id}: not found.")


def upload_cover(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId,
    cover: UploadFile | None = None
) -> None:
    update_item(item_id, {"status": DocStatus.COVER})
    if cover is not None:
        try:
            filename, contents = read_file_contents(cover)
            cover_path = upload_file(user_id, item_id, filename, contents)
        except Exception as exc:
            update_item(item_id, {"status": DocStatus.FAILED})
            raise LoggerOSError(
                logger,
                f"Upload failed for cover file :{filename}:, item_id :{item_id}:."
            ) from exc

        logger.info('Cover uploaded.')
    else:
        cover_path = get_default_cover_s3_key()

    update_item(item_id, {"cover_path": cover_path})

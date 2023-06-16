from typing import Any, cast

from beanie.odm.fields import PydanticObjectId
from pydantic import NonNegativeInt, PositiveInt

from app.config.logging import LoggerOSError, LoggerValueError, get_logger
from app.config.settings import get_settings
from app.models.base import IdModel
from app.models.blocks import (
    BaseBlock, BaseBlockOut, Block, BlockAudio, BlockDict, BlockIdAudioStatus, BlockOut,
    BunnetBlock, PageNumber, ShallowBlockDict,
)
from app.models.fields import AudioStatus
from app.models.spans import BaseSpan, BunnetSpan, Span, SpanIdBlockId, SpanOut
from app.routers.http_exceptions import (
    InternalServerErrorHTTPException, NotFoundHTTPException,
)
from app.utils.aws import async_delete_s3_objs_in_prefix, get_block_audio_s3_prefix

logger = get_logger(__name__)


########
def get_spans_out_from_head_non_head_spans_db(
    head_span_db: BaseSpan,
    non_head_spans_db: list[BaseSpan]
) -> list[SpanOut]:
    spans: list[SpanOut] = [BaseSpan.convert_to_span_out(head_span_db)]
    cur_span_id: PydanticObjectId | None = head_span_db.next_id
    if cur_span_id is None:
        return spans  # only head span in block

    non_head_spans_dict: dict[PydanticObjectId, BaseSpan] = {
        span.id: span for span in non_head_spans_db
    }
    while cur_span_id is not None:
        try:
            cur_span = non_head_spans_dict[cur_span_id]
        except KeyError as exc:
            raise LoggerOSError(
                logger, 'Linked list construction failed in span :{cur_span_id}:.'
            ) from exc

        spans.append(BaseSpan.convert_to_span_out(cur_span))
        cur_span_id = cur_span.next_id

    return spans


####
async def async_get_block_spans_out_db(block_id: PydanticObjectId) -> list[SpanOut]:
    # get head span
    head_span_db = await Span.find_one(
        {"block_id": block_id, "is_head": True}
    ).project(BaseSpan)
    if not head_span_db:
        raise NotFoundHTTPException(f"No head span found for block :{block_id}:.")

    # get block non-head spans
    non_head_spans_db = await Span.find(
        {"block_id": block_id, "is_head": None}
    ).project(BaseSpan).to_list()

    try:
        spans = get_spans_out_from_head_non_head_spans_db(
            head_span_db, non_head_spans_db
        )
    except (LoggerOSError, LoggerValueError) as exc:
        raise InternalServerErrorHTTPException(exc.msg)

    return spans


def get_block_spans_out_db(block_id: PydanticObjectId) -> list[SpanOut]:
    # get head span
    head_span_db = BunnetSpan.find_one(
        {"block_id": block_id, "is_head": True}
    ).project(BaseSpan).run()
    if not head_span_db:
        raise LoggerOSError(logger, f"No head span found for block :{block_id}:.")

    # get block non-head spans
    non_head_spans_db = BunnetSpan.find(
        {"block_id": block_id, "is_head": None}
    ).project(BaseSpan).to_list()

    return get_spans_out_from_head_non_head_spans_db(head_span_db, non_head_spans_db)


####
async def async_get_block_out_from_block_db(block: BaseBlockOut) -> BlockOut:
    spans = await async_get_block_spans_out_db(block.id)
    return BlockOut.construct_from_block(block, spans)


def get_block_out_from_block_db(block: BaseBlockOut) -> BlockOut:
    spans = get_block_spans_out_db(block.id)
    return BlockOut.construct_from_block(block, spans)


########
# GET
async def async_get_item_block_db(
    item_id: PydanticObjectId,
    block_id: PydanticObjectId,
) -> Block | None:
    block_db = await Block.find_one({"_id": block_id, "item_id": item_id})
    if block_db:
        return block_db

    return None


async def async_get_item_block_page_nb(
    item_id: PydanticObjectId,
    block_id: PydanticObjectId,
) -> NonNegativeInt | None:
    block = await Block.find_one(
        {"_id": block_id, "item_id": item_id}
    ).project(PageNumber)
    if block:
        return block.page_nb

    return None


####
def get_page_range_block_query_dict(
    item_id: PydanticObjectId,
    start_page: NonNegativeInt | None = None,
    end_page: PositiveInt | None = None
) -> dict[str, PydanticObjectId | dict[str, NonNegativeInt]]:
    block_query_dict: dict[
        str, PydanticObjectId | dict[str, NonNegativeInt]
    ] = {"item_id": item_id}
    if ((start_page is not None) or (end_page is not None)):
        block_query_dict["page_nb"] = {}
        aux_dict = cast(dict[str, NonNegativeInt], block_query_dict["page_nb"])
        if start_page is not None:
            aux_dict.update({"$gte": start_page})
        if end_page is not None:
            aux_dict.update({"$lt": end_page})

    return block_query_dict


async def async_get_item_head_block_id(
    item_id: PydanticObjectId,
    start_page: NonNegativeInt | None = None,
    end_page: PositiveInt | None = None
) -> PydanticObjectId | None:
    """
    Get id of item head block if :start_page: in [0, None].
    Otherwise, get the id of the first block after :start_page:.
    """
    id_model = await Block.find_one(
        {"item_id": item_id, "is_head": True}
    ).project(IdModel)
    if not id_model:
        raise NotFoundHTTPException(f"No head block found for item :{item_id}:.")

    head_block_id = id_model.id
    if ((start_page is None) or (start_page == 0)):
        return head_block_id

    # Get first block after start page
    # Check what is the page number of the first block after start page until end page
    block_query_dict = get_page_range_block_query_dict(
        item_id,
        start_page=start_page,
        end_page=end_page
    )
    block_query = await Block.find(
        block_query_dict
    ).sort("+page_nb").limit(1).project(PageNumber).to_list()

    if not block_query or len(block_query) == 0:
        return None  # No block found after :start_page:

    first_block_page_from_start = block_query[0].page_nb
    # Construct linked list to find first block in page :first_block_page_from_start:
    # fetch blocks from page 0 to page :first_block_page_from_start: (inclusive)
    first_blocks = await Block.find({
        "item_id": item_id,
        "page_nb": {"$lte": first_block_page_from_start}
    }).project(BaseBlock).to_list()

    block_dict = ShallowBlockDict.initialize(first_blocks)
    cur_block_id: PydanticObjectId | None = head_block_id
    while (cur_block_id is not None):
        cur_block = block_dict.get_block(cur_block_id)
        if cur_block.page_nb >= start_page:
            break
        cur_block_id = cur_block.next_id

    if cur_block_id is None:
        raise InternalServerErrorHTTPException(
            f"Could not construct block linked list until page :{start_page}: "
            f"for item :{item_id}:"
        )
    if cur_block.page_nb != first_block_page_from_start:
        raise InternalServerErrorHTTPException(
            f"First block in linked list found in page :{cur_block.page_nb}: but first "
            f"block in item found in page :{first_block_page_from_start}:."
        )
    head_block_id = cur_block_id

    return head_block_id


def get_item_head_block_id(item_id: PydanticObjectId) -> PydanticObjectId:
    id_model = BunnetBlock.find_one(
        {"item_id": item_id, "is_head": True}
    ).project(IdModel).run()
    if not id_model:
        raise NotFoundHTTPException(f"No head block found for item :{item_id}:.")

    return id_model.id
####


async def async_get_item_block_out_db(
    item_id: PydanticObjectId,
    block_id: PydanticObjectId,
) -> BlockOut | None:
    block_db = await Block.find_one(
        {"_id": block_id, "item_id": item_id}
    ).project(BaseBlockOut)
    if block_db:
        return await async_get_block_out_from_block_db(block_db)

    return None


async def async_get_prev_item_block_db(
    item_id: PydanticObjectId,
    block_id: PydanticObjectId,
) -> Block | None:
    prev_block_db = await Block.find_one({"next_id": block_id, "item_id": item_id})
    if prev_block_db:
        return prev_block_db

    return None


async def async_get_item_block_audio(
    item_id: PydanticObjectId,
    block_id: PydanticObjectId
) -> BlockAudio | None:
    block_audio = await Block.find_one(
        {"_id": block_id, "item_id": item_id}
    ).project(BlockAudio)
    if not block_audio:
        return None

    return block_audio


async def async_get_item_block_batch_audio_status(
    item_id: PydanticObjectId,
    block_ids: list[PydanticObjectId]
) -> list[BlockIdAudioStatus]:
    blocks = await Block.find({
        "_id": {"$in": block_ids},
        "item_id": item_id
    }).project(BlockIdAudioStatus).to_list()

    return blocks


def get_item_block_batch_audio_status(
    item_id: PydanticObjectId,
    block_ids: list[PydanticObjectId]
) -> list[BlockIdAudioStatus]:
    blocks = BunnetBlock.find({
        "_id": {"$in": block_ids},
        "item_id": item_id
    }).project(BlockIdAudioStatus).to_list()

    return blocks


def get_item_block_audio_status(
    item_id: PydanticObjectId,
    block_id: PydanticObjectId
) -> BlockIdAudioStatus:
    block_audio_status = BunnetBlock.find_one(
        {"_id": block_id, "item_id": item_id}
    ).project(BlockIdAudioStatus).run()
    if not block_audio_status:
        raise LoggerOSError(logger, f"Block :{block_id}: not found.")

    return block_audio_status


######
# LIST

async def async_list_item_block_audios_db(
    item_id: PydanticObjectId,
    block_ids: list[PydanticObjectId] | None = None
) -> list[BlockAudio]:
    block_query_dict: dict[str, Any] = {"item_id": item_id}
    if block_ids is not None:
        if not block_ids:
            return []
        block_query_dict["_id"] = {"$in": block_ids}

    return await Block.find(block_query_dict).project(BlockAudio).to_list()


async def async_list_item_block_ids_db(
    item_id: PydanticObjectId
) -> list[PydanticObjectId]:
    id_models = await Block.find({"item_id": item_id}).project(IdModel).to_list()
    return [id_model.id for id_model in id_models]


######
# PUT
def update_block(
    item_id: PydanticObjectId,
    block_id: PydanticObjectId,
    update_dict: dict[str, Any]
) -> None:
    for key in update_dict:
        if key not in BunnetBlock.keys():
            raise LoggerValueError(logger, f"key :{key}: is not a field of Block.")

    update_query = BunnetBlock.find_one(
        {"_id": block_id, "item_id": item_id}
    ).update({"$set": update_dict}).run()

    if update_query.matched_count < 1:
        raise LoggerOSError(logger, f"Block :{block_id}: not found.")


#######
# Batch

def construct_block_dict(
    blocks: list[BaseBlock],
    head_spans: list[SpanIdBlockId],
    spans: list[BaseSpan]
) -> BlockDict:
    if len(head_spans) != len(blocks):
        # Check that there is one head span per block
        raise LoggerOSError(
            logger, "The Number of head spans does not match the number of blocks."
        )

    # {block_id: {"block": block, "head_span_id": span_id, "spans": {span_id: Span}}
    block_dict = BlockDict.initialize(blocks)
    for head_span in head_spans:  # save head span id for each block
        block_dict.add_head_span(head_span)

    for span in spans:  # save blocks spans
        block_dict.add_span(span)

    return block_dict


def get_item_base_block_batch_db(
    item_id: PydanticObjectId,
    block_ids: list[PydanticObjectId]
) -> list[BaseBlock]:
    blocks_db = BunnetBlock.find({
        "_id": {"$in": block_ids},
        "item_id": item_id
    }).project(BaseBlock).to_list()

    if len(blocks_db) < len(block_ids):
        block_ids_db = [block_db.id for block_db in blocks_db]
        for block_id in block_ids:
            if block_id not in block_ids_db:
                raise LoggerOSError(logger, f"no block :{block_id}: found.")

    return blocks_db


def get_item_block_batch_dict(
    item_id: PydanticObjectId,
    block_ids: list[PydanticObjectId]
) -> BlockDict:
    # get batch blocks
    blocks = get_item_base_block_batch_db(item_id, block_ids)

    # get all block head spans (_id and block_id)
    head_spans = BunnetSpan.find({
        "block_id": {"$in": block_ids},
        "is_head": True
    }).project(SpanIdBlockId).to_list()

    # get all block spans
    spans = BunnetSpan.find(
        {"block_id": {"$in": block_ids}}
    ).project(BaseSpan).to_list()

    return construct_block_dict(blocks, head_spans, spans)


def get_cur_block(block_dict: BlockDict, cur_block_id: PydanticObjectId) -> BaseBlock:
    """Get current block from id and block_dict"""
    try:
        cur_block = block_dict.get_block(cur_block_id)
    except KeyError as exc:
        raise LoggerOSError(
            logger, "Linked list construction failed in block :{cur_block_id}:."
        ) from exc

    return cur_block


def append_cur_block_to_blocks(
    cur_block: BaseBlock,
    blocks: list[BlockOut],
    block_dict: BlockDict,
) -> None:
    """
    Returns:
        next block id (can be None if block is tail block)
    """
    block_spans: list[SpanOut] = []
    cur_span_id: PydanticObjectId | None = block_dict.get_head_span_id(cur_block.id)
    span_dict = block_dict.get_span_dict(cur_block.id)
    while cur_span_id is not None:
        cur_span = span_dict[cur_span_id]
        block_spans.append(BaseSpan.convert_to_span_out(cur_span))
        cur_span_id = cur_span.next_id

    if len(block_spans) != len(span_dict):
        raise LoggerOSError(
            logger, f"Could not construct span linked list for block :{cur_block.id}: "
        )

    blocks.append(BlockOut.construct_from_block(cur_block, block_spans))


async def async_get_item_block_batch_read_block_ids(
    item_id: PydanticObjectId,
    block_ids: list[PydanticObjectId] | None = None,
    only_missing: bool = False
) -> list[PydanticObjectId]:
    """
    Args:
        :block_ids: If not given, get all item read block ids
    """
    block_query_dict: dict[str, Any] = {
        "item_id": item_id,
        "read": {"$ne": False}
    }
    if block_ids is not None:
        if not block_ids:
            return []
        block_query_dict["_id"] = {"$in": block_ids}

    if only_missing:
        block_query_dict["audio_status"] = {"$ne": AudioStatus.COMPLETED}

    read_blocks_id_models = await Block.find(
        block_query_dict
    ).project(IdModel).to_list()

    return [id_model.id for id_model in read_blocks_id_models]


########
# DELETE
async def async_simple_delete_block_db(block_db: Block) -> bool:
    """
    Delete operation on single block; pointers of linked list are not updated.
    S3 objs are not deleted (see delete_item_block_db_s3() for that).
    """
    await Span.find({"block_id": block_db.id}).delete()  # delete spans
    delete_result = await block_db.delete()  # delete block
    if (delete_result is None or delete_result.deleted_count == 0):
        return False

    return True


async def async_delete_item_block_audio_s3(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId,
    block_id: PydanticObjectId
) -> None:
    if not get_settings().LOCAL:
        block_audio_s3_prefix = get_block_audio_s3_prefix(
            user_id, item_id, block_id
        )
        await async_delete_s3_objs_in_prefix(block_audio_s3_prefix)


async def async_delete_item_block_db_s3(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId,
    block_id: PydanticObjectId
) -> bool:
    block_db = await async_get_item_block_db(item_id, block_id)
    if not block_db:
        return False

    # initially, prev_block -> block -> next_block. Now, prev_block -> next_block.
    await Block.find_one(
        {"next_id": block_id, "item_id": item_id}
    ).update({"$set": {"next_id": block_db.next_id}})

    await async_delete_item_block_audio_s3(user_id, item_id, block_id)
    if not await async_simple_delete_block_db(block_db):
        return False

    return True

import os

from beanie.odm.fields import PydanticObjectId
from botocore.exceptions import ClientError

from app.config.logging import LoggerClientError, get_logger
from app.config.settings import DidWeRaise, get_settings
from app.config.variables import Path as VarConfig  # type: ignore
from app.models.blocks import BunnetBlock
from app.models.document import PageV2  # type: ignore
from app.models.spans import BunnetSpan
from app.models.validators import set_read_to_none_if_true
from app.utils.aws import (
    delete_s3_item, get_item_path, get_s3_item_obj_key, write_stream_to_s3,
)
from app.utils.general import mkdir_if_not_exists

logger = get_logger(__name__)


def upload_file(
    user_id: PydanticObjectId,
    item_id: PydanticObjectId,
    filename: str,
    contents: bytes
) -> str:
    s3_key = get_s3_item_obj_key(user_id, item_id, filename)
    if not get_settings().LOCAL:
        try:
            with DidWeRaise() as error_state:
                write_stream_to_s3(contents, s3_key)
        except ClientError as exc:
            raise LoggerClientError(logger, exc=exc)
        finally:
            if error_state.exception_happened:
                delete_s3_item(user_id, item_id)
    else:
        item_path = get_item_path(user_id, item_id)
        out_path = os.path.join(VarConfig.OUTPUT, item_path)
        mkdir_if_not_exists(out_path)

        with open(os.path.join(out_path, filename), 'wb') as f:
            f.write(contents)

    return s3_key


def insert_item_blocks_from_pages_db(
    item_id: PydanticObjectId,
    pages: list[PageV2],
) -> None:
    block_ids = [
        PydanticObjectId()
        for page in pages
        for _ in range(len(page.blocks))
    ]  # generate the maximum number of block_ids needed
    blocks: list[BunnetBlock] = []
    spans: list[BunnetSpan] = []
    block_idx = 0

    for page in pages:
        if not page.blocks:
            continue

        for block in page.blocks:
            block_id = block_ids[block_idx]
            span_ids = [PydanticObjectId() for _ in block.spans]
            num_spans = len(span_ids)
            for j, span in enumerate(block.spans):
                is_head_span = True if j == 0 else None  # None is equivalent to False
                span_next_id = (None if j >= (num_spans - 1) else span_ids[j + 1])
                # if block.read is False, ignore span.read. Otherwise, set span_read
                # to None if span.read is True or None. None is equivalent to True.
                span_read = (
                    None
                    if (block.read is False or span.read is not False)
                    else False
                )
                spans.append(
                    BunnetSpan(
                        id=span_ids[j],
                        block_id=block_id,
                        next_id=span_next_id,
                        is_head=is_head_span,
                        type_=None,
                        text=span.text,
                        read=span_read,
                    )
                )

            next_id = (
                None
                if block_idx >= (len(block_ids) - 1)
                else block_ids[block_idx + 1]
            )
            # is_head: None is equivalent to False
            is_head_block = True if block_idx == 0 else None
            # None is equivalent to True
            block_read = set_read_to_none_if_true(block.read)
            blocks.append(
                BunnetBlock(
                    id=block_id,
                    item_id=item_id,
                    next_id=next_id,
                    page_nb=page.number,
                    is_head=is_head_block,
                    read=block_read,
                    size_class=block.size_class
                )
            )
            block_idx += 1

    BunnetSpan.insert_many(spans)
    # needed because some blocks were skipped, so we never utilize all the ids,
    # above, which would be required to make the last block have next_id=None
    blocks[-1].next_id = None
    BunnetBlock.insert_many(blocks)

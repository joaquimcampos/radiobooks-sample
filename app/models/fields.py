from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any

from fastapi import Body, Query
from pydantic import Field
from pydantic.fields import Undefined


@unique
class BlockType(int, Enum):
    TEXT = 0
    IMAGE = 1
    TABLE = 2


@unique
class SpanType(int, Enum):
    TEXT = 0
    PAUSE = 1


@unique
class Tag(str, Enum):
    TITLE = "title"
    AUTHOR = "author"
    IMAGE = "image"
    TABLE = "table"
    CHAPTER = "chapter"
    SUB_CHAPTER = "sub-chapter"
    PAGE_NUMBER = "page number"
    FOOTER = "footer"
    HEADER = "header"


class SizeClassDiff(int, Enum):
    SMALLER = 1
    SAME = 0
    LARGER1 = 1
    LARGER2 = 2
    LARGER3 = 3


@unique
class SizeClass(str, Enum):
    SMALL = "small"  # SMALLER diff with main font
    BODY = "body"  # SAME diff with main font
    H3 = "h3"  # LARGER1 diff with main font
    H2 = "h2"  # LARGER2 diff with main font
    H1 = "h1"  # LARGER3 diff with main font


@unique
class DocStatus(str, Enum):
    IN_PROGRESS = "in progress"
    COMPLETED = "completed"
    FAILED = "failed"
    COVER = "cover"
    DOCUMENT = "document"


@unique
class AudioStatus(str, Enum):
    IN_PROGRESS = "in progress"
    COMPLETED = "completed"
    FAILED = "failed"


@unique
class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"


@unique
class AudioOptions(str, Enum):
    ALL = "all"
    MISSING = "missing"


def datetime_func():
    return datetime.now(timezone.utc)


def get_language_name_field(required: bool = True) -> Any:
    return Field(
        default=Undefined if required else None,
        description='Language (format: "some format")',
        max_length=5
    )


def get_voice_name_field(required: bool = True) -> Any:
    return Field(
        default=Undefined if required else None,
        description='Voice (format: "some format")',
    )


class Fields:
    """Fields that start with 'opt' are optional"""
    added_date = Field(default_factory=datetime_func)
    title = Field(max_length=100)
    author = Field(max_length=100)
    opt_nb_pages = Field(
        default=None,
        description="Number of pages in item document."
    )
    opt_cover_path = Field(
        default=None,
        description="Cover path. The full path is 'aws_root_path/:cover_path:'."
    )
    opt_document_path = Field(
        default=None,
        description="Document path. The full path is 'aws_root_path/:document_path:'."
    )
    opt_audio_path = Field(
        default=None,
        description="Audio path. The full path is 'aws_root_path/:audio_path:'."
    )
    review_progress = Field(
        default=0,
        ge=0,
        le=100,
        description="Review progress in percentage value."
    )
    opt_toc = Field(default=None, title="Table of contents")
    opt_span_type = Field(default=None, alias='type')
    opt_read = Field(
        default=None,
        description="Whether element is to be read. None is equivalent to True."
    )
    opt_inline_pause = Field(
        None,
        description=(
            "Inline pause in [ms] or None. If None, a default pause is selected."
        )
    )
    next_id = Field(
        description="If None, the element inserted at the tail of the list."
    )
    page_nb = Field(
        description="Page number (0-based index) to which block belongs to."
    )
    opt_is_head = Field(
        default=None,
        description="Whether element is head of list. None is equivalent to False."
    )
    opt_start_id = Field(
        default=None,
        description="If not given, :start_id: is the id of the head block."
    )
    opt_end_id = Field(
        default=None,
        description="If not given, :end_id: is the id of the last item block."
    )


class Queries:
    start_page = Query(
        description=":start_page: is included in the returned document."
    )
    end_page = Query(
        description=":end_page: is not included in the returned document."
    )
    audio_options = Query(
        description=(
            "If not given, do not generate audios. If :audios:=missing, "
            "generate only missing audios. Otherwise, generate all audios."
        )
    )
    audio_flag = Query(description="If set, generate audio(s).")
    only_missing_audio_flag = Query(
        description="If set, only generate missing audio(s)"
    )


class Bodies:
    prev_block_id_and_block = Body(
        description="New block to add and previous block id."
    )
    block_in = Body(description="The updated block model.")
    block_ids_list_or_range = Body(
        examples={
            "list": {
                "summary": "A list of block ids",
                "description": "Each element is a PydanticObjectId.",
                "value": {
                    "block_ids": [
                        "63becf2d42a96a2f6f1ba55a",
                        "63becf2d42a96a2f6f1ba55b"
                    ],
                }
            },
            "range": {
                "summary": "A start-end range of block ids",
                "description": (
                    "Blocks are fetched by following the linked list from "
                    ":start_id: to :end_id:. <br>"
                    ":start_id: defaults to the id of the head item block. <br>"
                    ":end_id: defaults to the id of the last item block. "
                ),
                "value": {
                    "start_id": "63becf2d42a96a2f6f1ba55a",
                    "end_id": "63becf2d42a96a2f6f1ba55b"
                }
            }
        }
    )

from __future__ import annotations

from beanie import Document as Document
from beanie.odm.fields import PydanticObjectId
from bunnet import Document as BunnetDocument
from pydantic import BaseModel, root_validator, validator

from app.models.base import IdModel
from app.models.collections import Collections
from app.models.fields import Fields, SpanType
from app.models.validators import (
    set_is_head_to_none_if_false, set_read_to_none_if_true,
    set_span_type_to_none_if_text,
)


class PauseSpanIn(BaseModel):
    pause: int | None = Fields.opt_inline_pause

    class Config:
        schema_extra = {
            "example": {
                "pause": "250"
            }
        }


class TextSpanIn(BaseModel):
    text: str
    read: bool | None = Fields.opt_read

    _set_read = validator('read', allow_reuse=True)(set_read_to_none_if_true)

    class Config:
        schema_extra = {
            "example": {
                "text": "This is a span.",
                "read": "True",
            }
        }


class SpanOut(BaseModel):
    type_: SpanType | None = Fields.opt_span_type
    pause: int | None = Fields.opt_inline_pause
    text: str | None = None
    read: bool | None = Fields.opt_read

    @root_validator
    def check_span_type_read(cls, values):
        values["read"] = set_read_to_none_if_true(values["read"])
        values["type_"] = set_span_type_to_none_if_text(values["type_"])

        return values

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "type_": "0",  # SpanType.TEXT
                **TextSpanIn.Config.schema_extra['example']
            }
        }


class SpanIdBlockId(IdModel):
    block_id: PydanticObjectId

    class Config:
        schema_extra = {
            "example": {
                "_id": "63becf2d42a96a2f6f1ba55a",
                "block_id": "65becf2d42a96a2f6f1ab41b"
            }
        }


class BaseSpan(SpanIdBlockId, SpanOut):
    next_id: PydanticObjectId | None = Fields.next_id
    is_head: bool | None = Fields.opt_is_head  # None is equivalent to False

    _set_is_head = validator('is_head', allow_reuse=True)(set_is_head_to_none_if_false)

    @classmethod
    def convert_to_span_out(cls, span: BaseSpan) -> SpanOut:
        return span

    class Config:
        schema_extra = {
            "example": {
                **SpanIdBlockId.Config.schema_extra['example'],
                "next_id": "65becf2d42a96a2f6f1ab41c",
                "is_head": False,
                **SpanOut.Config.schema_extra['example']
            }
        }


class Span(Document, BaseSpan):  # type: ignore
    id: PydanticObjectId

    class Settings:
        name = Collections.SPANS.value
        schema_extra = BaseSpan.Config.schema_extra
        use_state_management = True
        use_enum_values = True


class BunnetSpan(BunnetDocument, BaseSpan):  # type: ignore
    id: PydanticObjectId  # type: ignore

    class Settings:
        name = Collections.SPANS.value
        schema_extra = BaseSpan.Config.schema_extra
        use_state_management = True
        use_enum_values = True

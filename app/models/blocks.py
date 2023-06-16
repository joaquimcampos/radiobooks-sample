from __future__ import annotations

from functools import cache
from typing import cast

from beanie import Document as Document
from beanie.odm.fields import PydanticObjectId
from bunnet import Document as BunnetDocument
from pydantic import BaseModel, Field, NonNegativeInt, validator

from app.models.base import IdModel
from app.models.collections import Collections
from app.models.fields import AudioStatus, Fields, SizeClass
from app.models.spans import BaseSpan, PauseSpanIn, SpanIdBlockId, SpanOut, TextSpanIn
from app.models.validators import set_is_head_to_none_if_false, set_read_to_none_if_true


class BlockIdListIn(BaseModel):
    block_ids: list[PydanticObjectId]

    def __iter__(self):
        return self.block_ids.__iter__()

    class Config:
        schema_extra = {
            "example": {
                "block_ids": [
                    "63becf2d42a96a2f6f1ba55a",
                    "63becf2d42a96a2f6f1ba55b"
                ],
            }
        }


class BlockIdRange(BaseModel):
    start_id: PydanticObjectId | None = Fields.opt_start_id
    end_id: PydanticObjectId | None = Fields.opt_end_id

    class Config:
        schema_extra = {
            "example": {
                "start_id": "63becf2d42a96a2f6f1ba55a",
                "end_id": "63becf2d42a96a2f6f1ba55b"
            }
        }


class BlockIdAudioStatus(IdModel, BaseModel):
    audio_status: AudioStatus | None = None

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True
        fields = {"id": "_id"}
        schema_extra = {
            "example": {
                "_id": "63becf2d42a96a2f6f1ba55a",
                "audio_status": AudioStatus.IN_PROGRESS
            }
        }


class BlockAudio(BlockIdAudioStatus):
    audio_path: str | None = Fields.opt_audio_path

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True
        fields = {"id": "_id"}
        schema_extra = {
            "example": {
                **BlockIdAudioStatus.Config.schema_extra["example"],
                "audio_path": "some_audio_path.wav"
            }
        }


class PageNumber(BaseModel):
    page_nb: NonNegativeInt = Fields.page_nb


class BlockAux(BaseModel):
    size_class: SizeClass | None = None

    class Config:
        use_enum_values = True  # https://docs.pydantic.dev/usage/model_config/


class BlockIn(BlockAux):
    spans: list[TextSpanIn | PauseSpanIn]


class BlockInPrevId(BaseModel):
    prev_block_id: PydanticObjectId | None = Field(
        None,
        description="If not given, the block inserted at the beggining of block list."
    )
    block: BlockIn


class BlockAuxRead(BlockAux):
    read: bool | None = Fields.opt_read  # None is equivalent to True

    _set_read = validator('read', allow_reuse=True)(set_read_to_none_if_true)


class BaseBlockOut(IdModel, BlockAuxRead):

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True
        fields = {"id": "_id"}


class BlockOut(BaseBlockOut):
    spans: list[SpanOut]

    @classmethod
    def construct_from_block(
        cls,
        block: BaseBlockOut,
        spans: list[SpanOut]
    ) -> BlockOut:
        return cls.parse_obj({
            **block.dict(),
            "spans": spans
        })


class BaseBlock(BaseBlockOut):
    item_id: PydanticObjectId
    next_id: PydanticObjectId | None = Fields.next_id
    page_nb: NonNegativeInt = Fields.page_nb
    is_head: bool | None = Fields.opt_is_head  # None is equivalent to False
    audio_status: AudioStatus | None = None
    audio_path: str | None = Fields.opt_audio_path

    _set_is_head = validator('is_head', allow_reuse=True)(set_is_head_to_none_if_false)


class ShallowBlockDict(BaseModel):
    # {block_id: {"block": block}}
    __root__: dict[PydanticObjectId, dict[str, BaseBlock]]

    @classmethod
    def initialize(cls, blocks: list[BaseBlock]) -> ShallowBlockDict:
        return cls.parse_obj({
            block.id: {"block": block} for block in blocks
        })

    def get_block(self, block_id: PydanticObjectId) -> BaseBlock:
        return cast(BaseBlock, self.__root__[block_id]["block"])


class BlockDict(BaseModel):
    # {block_id: {"block": block, "head_span_id": span_id, "spans": {span_id: Span}}
    __root__: dict[
        PydanticObjectId,
        dict[str, BaseBlock | PydanticObjectId | dict[PydanticObjectId, BaseSpan]]
    ]

    @classmethod
    def initialize(cls, blocks: list[BaseBlock]) -> BlockDict:
        return cls.parse_obj({
            block.id: {"block": block, "spans": {}} for block in blocks
        })

    def get_head_span_id(self, block_id: PydanticObjectId) -> PydanticObjectId:
        return cast(  # get head span id
            PydanticObjectId,
            self.__root__[block_id]["head_span_id"]
        )

    def get_block(self, block_id: PydanticObjectId) -> BaseBlock:
        return cast(BaseBlock, self.__root__[block_id]["block"])

    def get_span_dict(
        self,
        block_id: PydanticObjectId
    ) -> dict[PydanticObjectId, BaseSpan]:
        return cast(
            dict[PydanticObjectId, BaseSpan],
            self.__root__[block_id]["spans"]
        )

    def add_head_span(self, head_span: SpanIdBlockId) -> None:
        self.__root__[head_span.block_id]["head_span_id"] = head_span.id

    def add_span(self, span: BaseSpan) -> None:
        span_dict = self.get_span_dict(span.block_id)
        span_dict[span.id] = span


class Block(Document, BaseBlock):  # type: ignore
    id: PydanticObjectId

    class Settings:
        name = Collections.BLOCKS.value
        use_state_management = True
        use_enum_values = True  # https://docs.pydantic.dev/usage/model_config/


# NOTE: Sync between Bunnet/Beanie and is_root with inheritance is not working properly
class BunnetBlock(BunnetDocument, BaseBlock):  # type: ignore
    id: PydanticObjectId  # type: ignore

    @classmethod
    @cache
    def keys(cls) -> list[str]:
        return list(cls.__fields__.keys())

    class Settings:
        name = Collections.BLOCKS.value
        use_state_management = True
        use_enum_values = True

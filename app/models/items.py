from __future__ import annotations

from datetime import datetime
from functools import cache

# import pymongo
from beanie import Document as Document
from beanie.odm.fields import PydanticObjectId
from bunnet import Document as BunnetDocument
from pydantic import BaseModel, PositiveInt

from app.models.base import IdModel
from app.models.blocks import BlockOut
from app.models.collections import Collections
from app.models.fields import AudioStatus, DocStatus, Fields
from app.models.toc import TocItemModel  # type: ignore
from app.models.voices import VoiceInfo  # type: ignore


class ItemIdDocStatus(IdModel):
    status: DocStatus = DocStatus.IN_PROGRESS

    class Config:
        schema_extra = {
            "example": {
                "_id": "63becf2d42a96a2f6f1ba55a",
                "status": DocStatus.IN_PROGRESS,
            }
        }


class ItemIn(VoiceInfo):
    title: str = Fields.title
    author: str = Fields.author

    class Config:
        schema_extra = {
            "example": {
                "title": "As It Is",
                "author": "Tulku Urgyen Rinpoche",
                **VoiceInfo.Config.schema_extra['example']
            }
        }


class ItemAux(ItemIn):
    added_date: datetime = Fields.added_date
    status: DocStatus = DocStatus.IN_PROGRESS

    class Config:
        schema_extra = {
            "example": {
                **ItemIn.Config.schema_extra['example'],
                "added_date": "2023-02-22T11:44:18.274385",
                "status": DocStatus.IN_PROGRESS
            }
        }


class CoverInfo(BaseModel):
    cover_path: str | None = Fields.opt_cover_path

    class Config:
        schema_extra = {
            "example": {
                "cover_path": "some_cover_path.png",
            }
        }


class ItemInfo(ItemAux, CoverInfo):

    class Config:
        schema_extra = {
            "example": {
                **ItemAux.Config.schema_extra['example'],
                **CoverInfo.Config.schema_extra['example']
            }
        }


class BasicItem(IdModel, ItemInfo):
    class Config:
        schema_extra = {
            "example": {
                **IdModel.Config.schema_extra['example'],
                **ItemInfo.Config.schema_extra['example']
            }
        }


class ItemAuxPlus(ItemAux):
    toc: list[TocItemModel] | None = Fields.opt_toc
    document_path: str | None = Fields.opt_document_path
    nb_pages: PositiveInt | None = Fields.opt_nb_pages


class BaseItemOut(IdModel, ItemAuxPlus):
    owner_id: PydanticObjectId

    class Config:
        allow_population_by_field_name = True
        fields = {"id": "_id"}


class ItemOut(BaseItemOut):
    blocks: list[BlockOut]

    @classmethod
    def construct_from_item(
        cls,
        item: BaseItemOut,
        blocks: list[BlockOut]
    ) -> ItemOut:
        return cls.parse_obj({
            **item.dict(),
            "blocks": blocks
        })


class BaseItem(BaseItemOut):
    audio_status: AudioStatus | None = None
    audio_path: str | None = Fields.opt_audio_path
    cover_path: str | None = Fields.opt_cover_path


class Item(Document, BaseItem):  # type: ignore
    id: PydanticObjectId

    class Settings:
        name = Collections.ITEMS.value
        use_state_management = True


# e.g. that find of head block returns only one block, or that following the list
# gives the number of blocks with item_id = item.id
class BunnetItem(BunnetDocument, BaseItem):  # type: ignore
    id: PydanticObjectId  # type: ignore

    @classmethod
    @cache
    def keys(cls) -> list[str]:
        return list(cls.__fields__.keys())

    class Settings:
        name = Collections.ITEMS.value
        use_state_management = True

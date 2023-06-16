# import pymongo
# from pymongo import IndexModel
from beanie import Document
from beanie.odm.fields import PydanticObjectId
from pydantic import BaseModel, EmailStr

from app.models.collections import Collections


class BasicUser(BaseModel):
    id: PydanticObjectId
    username: str
    disabled: bool = False

    class Config:
        allow_population_by_field_name = True
        fields = {"id": "_id"}
        schema_extra = {
            "example": {
                "_id": "63becf2d42a96a2f6f1ba55a",
                "disabled": "False",
            }
        }


class UserInDB(Document):
    id: PydanticObjectId
    username: str
    email: EmailStr | None = None
    disabled: bool = False
    hashed_password: str

    class Settings:
        name = Collections.USERS.value
        use_state_management = True

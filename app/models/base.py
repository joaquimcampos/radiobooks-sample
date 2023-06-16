from beanie.odm.fields import PydanticObjectId
from pydantic import BaseModel


class IdModel(BaseModel):
    id: PydanticObjectId

    class Config:
        allow_population_by_field_name = True
        fields = {"id": "_id"}
        schema_extra = {
            "example": {
                "_id": "63becf2d42a96a2f6f1ba55a",
            }
        }

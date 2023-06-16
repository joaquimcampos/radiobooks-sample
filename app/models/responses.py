from pydantic import BaseModel


class ShortResponse(BaseModel):
    message: str

    class Config:
        schema_extra = {
            "example": {
                "message": "OK",
            }
        }

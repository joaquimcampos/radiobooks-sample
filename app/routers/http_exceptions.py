from fastapi import status
from fastapi.exceptions import HTTPException
from pydantic import BaseModel


class HTTPError(BaseModel):
    detail: str

    class Config:
        schema_extra = {
            "example": {"detail": "HTTPException raised."},
        }


class NotFoundHTTPException(HTTPException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail if detail else "The requested resource was not found.",
        )
    response = {
        "model": HTTPError,
        "description": "Not Found Error"
    }


class UnsupportedMediaTypeHTTPException(HTTPException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(detail
                    if detail
                    else "The requested resource has an invalid media type."),
        )
    response = {
        "model": HTTPError,
        "description": "Invalid Media Type"
    }


class BadRequestHTTPException(HTTPException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(detail if detail else "The request is invalid."),
        )
    response = {
        "model": HTTPError,
        "description": "Invalid Request"
    }


class InternalServerErrorHTTPException(HTTPException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(detail if detail else "Error occured in server."),
        )
    response = {
        "model": HTTPError,
        "description": "Internal Server Error"
    }


class BadGatewayHTTPException(HTTPException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(detail if detail else "Error occured in an associated service."),
        )
    response = {
        "model": HTTPError,
        "description": "Bad Gateway"
    }


class UnauthorizedHTTPException(HTTPException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(detail
                    if detail
                    else "Unauthorized access. Access denied."),
            headers={"WWW-Authenticate": "Bearer"}
        )
    response = {
        "model": HTTPError,
        "description": "Invalid Credentials"
    }

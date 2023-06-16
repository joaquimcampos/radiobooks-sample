from typing import Type

from fastapi import UploadFile

from app.routers.http_exceptions import UnsupportedMediaTypeHTTPException
from app.utils.enums import ExtendedEnum


class FileMimeTypes(str, ExtendedEnum):
    PDF = "application/pdf"
    EPUB = "application/epub+zip"


class FileExtensions(str, ExtendedEnum):
    PDF = ".pdf"
    EPUB = ".epub"


class ImgMimeTypes(str, ExtendedEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"


class ImgExtensions(str, ExtendedEnum):
    JPG = ".jpg"
    JPEG = ".jpeg"
    PNG = ".png"


def verify_file(
    file: UploadFile,
    MimeTypes: Type[ExtendedEnum],
    Extensions: Type[ExtendedEnum]
) -> None:
    if file.content_type not in MimeTypes.values():
        raise UnsupportedMediaTypeHTTPException(
            detail=("the file type is '{file.content_type}' "
                    "is not of type "
                    f"[{', '.join([str(v) for v in MimeTypes.values()])}].")
        )
    elif (file.filename is None or
            not file.filename.endswith(tuple(Extensions.values()))):
        raise UnsupportedMediaTypeHTTPException(
            detail=("the file '{file.filename}' "
                    "does not end with extension "
                    f"[{', '.join([str(v) for v in Extensions.values()])}].")
        )


def verify_item_file(file: UploadFile) -> None:
    verify_file(file, MimeTypes=FileMimeTypes, Extensions=FileExtensions)


def verify_image_file(file: UploadFile) -> None:
    verify_file(file, MimeTypes=ImgMimeTypes, Extensions=ImgExtensions)

from io import BufferedReader, BytesIO
from typing import Any

from app.models.document import TDocCls, TDocObj  # type: ignore


def convert_doc_obj_to_doc_class(
    obj: TDocObj,
    new_cls: TDocCls,
    set_fields: dict[Any, Any] | None = None
) -> TDocObj:
    new_model_dict = obj.dict(include={
        field for field in new_cls.__fields__
        if field in obj.__fields__
    })

    new_model_dict['rect'] = obj.rect.copy()  # default
    if set_fields is not None:
        new_model_dict = {**new_model_dict, **set_fields}  # second takes precendence
        if 'rect' in set_fields:
            new_model_dict['rect'] = set_fields['rect'].copy()

    return new_cls.construct(**new_model_dict)


def get_file_buffered_reader(pdf_contents: bytes) -> BufferedReader:
    file_handle = BytesIO()
    file_handle.write(pdf_contents)
    file_handle.seek(0)

    return BufferedReader(file_handle)  # type: ignore

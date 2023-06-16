from app.models.fields import SpanType


def set_read_to_none_if_true(read: bool | None) -> bool | None:
    return (None if read is True else read)


def set_span_type_to_none_if_text(type_: SpanType) -> SpanType | None:
    return (None if type_ == SpanType.TEXT else type_)


def set_is_head_to_none_if_false(is_head: bool | None) -> bool | None:
    return (None if is_head is False else is_head)

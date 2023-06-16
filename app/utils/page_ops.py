from typing import Callable

from app.models.document import BlockV1, PageV1, PageV2  # type: ignore
from app.models.fields import BlockType
from app.models.geometry import point_like
from app.utils.geometry import get_sorting_tuple


def join_same_font_spans(pageV2: PageV2) -> None:
    """Join spans with same font and dehyphenate."""
    # spans need to be joined if they belong to different lines
    for block in pageV2.blocks:
        rm_span_idx: list[int] = []
        for j in range(len(block.spans) - 1):
            this_span = block.spans[j]
            next_span = block.spans[j + 1]
            if this_span.has_same_font(next_span):
                next_span.include_previous_span(this_span)  # also dehyphenates
                rm_span_idx.append(j)  # signal this_span for removal

        # Remove spans merged with next
        block.spans[:] = [
            span for j, span in enumerate(block.spans)
            if j not in rm_span_idx
        ]


def preprocess(pageV1: PageV1):
    """
    Preprocess page by removing empty lines, empty blocks, and adding a newline
    to the last span in each line.
    """
    rm_block_idx: list[int] = []
    for i, block in enumerate(pageV1.blocks):
        block.page_number = pageV1.number  # add page number to block
        assert block.type_ == BlockType.TEXT, (
            f'block of type {block.type_} != {BlockType.TEXT} (text) found.'
        )
        rm_line_idx: list[int] = []
        for j, line in enumerate(block.lines):
            line_txt = ''.join(spanV1.text for spanV1 in line.spans)
            if not line_txt or line_txt.isspace():
                rm_line_idx.append(j)  # flag empty line for removal
            else:
                line.spans[-1].text += '\n'  # Add newline to last span in line

        # remove empty lines
        block.lines[:] = [
            line for j, line in enumerate(block.lines)
            if j not in rm_line_idx
        ]
        if not block.lines:
            rm_block_idx.append(i)  # flag empty block for removal

    pageV1.blocks[:] = [
        block for i, block in enumerate(pageV1.blocks)
        if i not in rm_block_idx
    ]

    # sort blocks
    sort_key: Callable[
        [BlockV1],
        point_like
    ] = lambda block: get_sorting_tuple(block.rect)
    pageV1.blocks.sort(key=sort_key)

"""General utilities"""
import os
import re

from app.config.variables import Regex as VarConfig


def mkdir_if_not_exists(path: str) -> None:
    if not os.path.isdir(path):
        os.umask(0)
        os.makedirs(path, mode=0o777, exist_ok=True)


def abs_relative_diff(s1: int | float, s2: int | float) -> float:
    """
    Return the size difference between :s1 and :s2 relative to :s2.
    """
    assert s1 > 0 and s2 > 0, f's1: {s1}, s2: {s2}.'
    return (float(abs(s1 - s2)) / float(s2))


def rm_whitespaces(txt: str) -> str:
    return re.sub(VarConfig.WHITESPACES_REGEX, "", txt)


def contains_only_punctuation_or_whitespaces(txt: str) -> bool:
    search = re.compile(r'[^{}]'.format(VarConfig.PUNCTUATION_REGEX)).search
    return not bool(search(rm_whitespaces(txt)))


def is_end_of_sentence(txt: str) -> bool:
    return (
        bool(re.findall(VarConfig.SENTENCE_END_REGEX_END, txt)) or
        contains_only_punctuation_or_whitespaces(txt)
    )


def relative_value(s1: int | float, s2: int | float) -> float:
    """
    Return the value of :s1 relative to :s2.
    :s2 needs to be larger than :s1.
    """
    assert s1 >= 0 and s2 >= 0, f's1: {s1}, s2: {s2}.'
    if s2 < s1:
        raise ValueError('Invalid inputs: '
                         's2 = {:.2f} < {:.2f} = s1'.format(s2, s1))
    return (float(s1) / float(s2))

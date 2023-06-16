"""Global variable configuration"""
from typing import Final, Literal


class Object:
    # list of pages where to extract images and tables.
    # If None, objects are extracted in all pages
    IMAGE_PAGES: list[int] | Literal["all"] = "all"
    TABLE_PAGES: list[int] | Literal["all"] = []


class Regex:
    SEMICOLON_REGEX_END: Final[str] = (
        r"(?:(?![×Þß÷þø])[a-zA-Zà-ÿÀ-Ÿα-ωΑ-Ωά-ώ0-9\u00BB]){1}" +
        r"[ \u00A0]{0,1}" +
        r"[;]+" +
        r"[ \d\u00A0\u00BB\t\r\x0b\x0c\n]*$"
    )
    SENTENCE_END_REGEX_END: Final[str] = (
        r"(?:(?![×Þß÷þø])[a-zA-Zà-ÿÀ-Ÿα-ωΑ-Ωά-ώ0-9\u00BB]){1}" +
        r"[ \u00A0]{0,1}" +
        r"[.!?]+" +
        r"[ \d\u00A0\u00BB\t\r\x0b\x0c\n]*$"
    )
    ITEMIZE_START_REGEX: Final[str] = (
        r"^([A-Z\d]*[ \u00A0]*" +  # e.g. A. [text], 1A. [text]
        r"[.\u2022\u2023\u2043\u2055\u2010]{1}" +  # itemize symbols
        "[ \u00A0\t\r\x0b\x0c]+)"
    )
    HYPHEN_END_REGEX: Final[str] = r"[-\u00ad]+[ ]{0,1}[\n]*$"
    PUNCTUATION_REGEX: Final[str] = r".!?;"
    ROMAN_NUMERALS: Final[str] = 'MDCLXVI()'
    WHITESPACES_REGEX: Final[str] = r"[ \u00A0\t\r\x0b\x0c\n]+"


class AWS:
    # The maximum number of concurrent S3 API transfer operations can be tuned to
    # adjust for the connection speed. Set the max_concurrency attribute to increase
    # or decrease bandwidth usage.
    # The attribute's default setting is 10. To reduce bandwidth usage, reduce the
    # value; to increase usage, increase it.
    NUM_WORKERS: int = 20
    PRESIGNED_URL_EXPIRE_SECONDS: Final[int] = 14400  # 4 hours

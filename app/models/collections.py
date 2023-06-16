from enum import Enum, unique


@unique
class Collections(str, Enum):
    USERS = "users"
    ITEMS = "items"
    BLOCKS = "blocks"
    SPANS = "spans"

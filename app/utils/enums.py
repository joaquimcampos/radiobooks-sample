from enum import Enum


class ExtendedEnum(Enum):

    @classmethod
    def values(cls):
        return map(lambda c: c.value, cls)

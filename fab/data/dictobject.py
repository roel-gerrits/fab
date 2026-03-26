from typing import override
from .base import Object
from collections.abc import Mapping, Sequence


class DictObject(Object):
    def __init__(self, attributes: Mapping[str, Object]) -> None:
        self.__attributes = attributes

    @override
    def has_attr(self, name: str) -> bool:
        return name in self.__attributes

    @override
    def attrs(self) -> Sequence[str]:
        return list(self.__attributes.keys())

    @override
    async def get_attr(self, name: str) -> Object:
        return self.__attributes[name]

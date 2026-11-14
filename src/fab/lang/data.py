from __future__ import annotations
import glob

import pathlib
from collections.abc import Sequence
from typing import override

from .data_base import (
    EvaluationContext,
    Function,
    FunctionCallError,
    Object,
    ObjectWithMethods,
)
from .util import parse_args


class String(Object):
    value: str

    def __init__(self, value: str) -> None:
        self.value = value

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, String):
            return False
        return self.value == other.value

    @override
    def __repr__(self) -> str:
        return f'<String "{self.value}">'


class List(ObjectWithMethods):
    items: Sequence[Object]

    def __init__(self, items: Sequence[Object]) -> None:
        super().__init__()
        self.items = items

        class MapFunc(Function):
            @override
            async def call(
                self,
                context: EvaluationContext,
                args: list[Object],
                kwargs: dict[str, Object],
            ) -> Object:
                map_func = args[0]
                assert isinstance(map_func, Function)

                mapped_items = [
                    await map_func.call(context, [item], {}) for item in items
                ]
                return List(mapped_items)

        self.add_method("map", MapFunc())

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, List):
            return False
        return self.items == other.items


class PathObj(ObjectWithMethods):
    path: pathlib.Path

    def __init__(self, path: pathlib.Path) -> None:
        super().__init__()
        self.path = path

        class SubpathFunc(Function):
            @override
            async def call(
                self,
                context: EvaluationContext,
                args: list[Object],
                kwargs: dict[str, Object],
            ) -> Object:
                (subpath_arg,) = parse_args(args, (String,))

                new_path = path / subpath_arg.value

                if not new_path.exists():
                    raise FunctionCallError(
                        f"Subpath '{subpath_arg.value}' ({new_path}) does not exist"
                    )
                return PathObj(new_path)

        self.add_method("subpath", SubpathFunc())

        class GlobFunc(Function):
            @override
            async def call(
                self,
                context: EvaluationContext,
                args: list[Object],
                kwargs: dict[str, Object],
            ) -> Object:
                (pattern_arg,) = parse_args(args, (String,))

                entries = []
                for entry in glob.glob(
                    pattern_arg.value, root_dir=path, recursive=True
                ):
                    entry_path = path / entry
                    entries.append(PathObj(entry_path))

                return List(entries)

        self.add_method("glob", GlobFunc())

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, PathObj):
            return False
        return self.path == other.path


# class EvaluationContext(ABC):
#     @abstractmethod
#     def apply_filename(self, path: pathlib.Path) -> None: ...
#
#     @abstractmethod
#     def get_current_file(self) -> pathlib.Path: ...
#
#     @abstractmethod
#     async def execute_operation(self, operation: Operation) -> Any: ...
#
#     @property
#     @abstractmethod
#     def buildins(self) -> Mapping[str, Object]: ...
#
#
# class FunctionCallError(Error):
#     pass
#
#
# class Function(Object, ABC):
#     @abstractmethod
#     async def call(
#         self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
#     ) -> Object: ...

from __future__ import annotations

import abc
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import override

from . import astree
from ..data.base import List, String, Function, Object
from ..data.operation import Operation
from ..building import Context
from .parser import parse


class EvaluationError(RuntimeError):
    pass


class FileLookup(abc.ABC):
    @abc.abstractmethod
    def lookup(self, name: str) -> str: ...


class FileLookupError(EvaluationError):
    pass


class LocalFileLookup(FileLookup):
    base: Path

    def __init__(self, base: Path) -> None:
        self.base = base

    @override
    def lookup(self, name: str) -> str:
        subpath = Path(name)
        if subpath.is_absolute():
            raise FileLookupError(f"Cannot lookup '{subpath}', path must be relative")

        path = self.base / subpath
        if not path.is_file():
            raise FileLookupError(
                f"Lookup of '{name}' failed: '{path}' does not exist or is not a file"
            )

        return path.read_text()


def evaluate_source(evaluator: Evaluator, source: str) -> Object:
    assignments = parse(source)

    class LazyLoader(Object):
        @override
        def has_attr(self, name: str) -> bool:
            return name in assignments

        @override
        def attrs(self) -> Sequence[str]:
            return list(assignments.keys())

        @override
        async def get_attr(self, name: str) -> Object:
            return await evaluator.evaluate(assignments[name], assignments)

    return LazyLoader()


class LoadFileFunc(Function):
    def __init__(self, file_lookup: FileLookup, evaluator: Evaluator):
        self.__file_lookup = file_lookup
        self.__evaluator = evaluator

    @override
    def call(self, args: list[Object], kwargs: dict[str, Object]) -> Object:
        assert isinstance(args[0], String)
        filename = args[0].value
        source = self.__file_lookup.lookup(filename)
        return evaluate_source(self.__evaluator, source)


class Evaluator:
    def __init__(self, context: Context) -> None:
        self.__context = context
        self.__symbols: dict[str, Object] = dict()
        pass

    def add_symbol(self, name: str, object: Object):
        self.__symbols[name] = object

    async def evaluate(
        self, expr: astree.Expression, assignments: Mapping[str, astree.Expression]
    ) -> Object:
        # if isinstance(expr, astree.Constant):
        #     return await self.evaluate_constant(expr)
        if isinstance(expr, astree.Variable):
            return await self.evaluate_variable(expr, assignments)
        elif isinstance(expr, astree.LiteralString):
            return await self.evaluate_literal_string(expr, assignments)
        elif isinstance(expr, astree.List):
            return await self.evaluate_list(expr, assignments)
        elif isinstance(expr, astree.AttributeRef):
            return await self.evaluate_attribute_ref(expr, assignments)
        elif isinstance(expr, astree.Call):
            return await self.evaluate_call(expr, assignments)

        raise NotImplementedError

    async def evaluate_variable(
        self, expr: astree.Variable, assignments: Mapping[str, astree.Expression]
    ) -> Object:
        var_name = expr.name.name
        if var_name in self.__symbols:
            return self.__symbols[var_name]
        if var_name not in assignments:
            raise EvaluationError(f"No variable named '{var_name}'")
        return await self.evaluate(assignments[var_name], assignments)

    async def evaluate_literal_string(
        self, expr: astree.LiteralString, assignments: Mapping[str, astree.Expression]
    ) -> Object:
        return String(expr.value)

    async def evaluate_list(
        self, expr: astree.List, assignments: Mapping[str, astree.Expression]
    ) -> Object:
        evaluated_items = [
            await self.evaluate(item, assignments) for item in expr.items
        ]
        return List(evaluated_items)

    async def evaluate_attribute_ref(
        self, expr: astree.AttributeRef, assignments: Mapping[str, astree.Expression]
    ) -> Object:
        evaluated_target = await self.evaluate(expr.target, assignments)
        attr_name = expr.name.name
        if not evaluated_target.has_attr(attr_name):
            raise EvaluationError(f"No attribute named '{attr_name}'")
        return await evaluated_target.get_attr(attr_name)

    async def evaluate_call(
        self, expr: astree.Call, assignments: Mapping[str, astree.Expression]
    ) -> Object:
        evaluated_target = await self.evaluate(expr.target, assignments)
        evaluated_args = [
            await self.evaluate(arg, assignments) for arg in expr.pos_args
        ]
        evaluated_kwargs = {
            kw.name: await self.evaluate(arg, assignments)
            for kw, arg in expr.key_args.items()
        }

        if isinstance(evaluated_target, Function):
            return await self.evaluate_function_call(
                evaluated_target, evaluated_args, evaluated_kwargs
            )
        elif isinstance(evaluated_target, Operation):
            return await self.evaluate_operation_call(
                evaluated_target, evaluated_args, evaluated_kwargs
            )
        else:
            raise EvaluationError("Target is not a function or action")

    async def evaluate_function_call(
        self,
        target: Function,
        args: list[Object],
        kwargs: dict[str, Object],
    ) -> Object:
        return target.call(args, kwargs)

    async def evaluate_operation_call(
        self,
        target: Operation,
        args: list[Object],
        kwargs: dict[str, Object],
    ) -> Object:
        return await target.execute(self.__context, args, kwargs)

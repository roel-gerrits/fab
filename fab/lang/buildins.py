from copy import copy
from pathlib import Path
from typing import override

from fab.lang.util import DictObject

from ..operations.gcc import GccCompile, GccLink, GccCollectCompileCommands
from ..operations.containerized_gcc import (
    GccCompile as ContainerizedGccCompile,
    GccLink as ContainerizedGccLink,
)

from ..operations import Extract, HttpArchive, HttpGet
from .data import EvaluationContext, Function, List, Object, PathObj, String, FunctionCallError
from .evaluator import evaluate_context


class LoadFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        assert isinstance(args[0], String)
        filename = Path(args[0].value)

        if filename.is_absolute():
            raise FunctionCallError("Cannot load absolute path")

        new_context = copy(context)
        new_context.apply_filename(filename)

        return evaluate_context(new_context)


class PathFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        assert isinstance(args[0], String)
        path_str = args[0].value
        working_dir = context.get_current_file().parent
        path = working_dir / path_str
        if not path.exists():
            raise FunctionCallError(f"No such path '{path_str}' ('{path}')")

        return PathObj(path)


class LinkFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        assert isinstance(args[0], PathObj)
        target_path = args[0].path

        destination = context.get_current_file().parent
        link_path = destination / target_path.name

        if link_path.exists():
            if not link_path.is_symlink():
                raise FunctionCallError(
                    f"Link target already exists and is not a symlink '{link_path}'"
                )

            link_path.unlink()

        link_path.symlink_to(target_path)

        return PathObj(link_path)


class HttpGetFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        assert isinstance(args[0], String)
        url = args[0].value
        op = HttpGet(url)
        result = await context.execute_operation(op)
        return PathObj(result)


class ExtractFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        assert isinstance(args[0], PathObj)
        archive = args[0].path
        op = Extract(archive)
        result = await context.execute_operation(op)
        return PathObj(result)


class HttpArchiveFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        assert isinstance(args[0], String)
        url = args[0].value
        op = HttpArchive(url)
        result = await context.execute_operation(op)
        return PathObj(result)


class GccCompileFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        assert isinstance(args[0], PathObj)
        assert isinstance(kwargs["includes"], List)
        source = args[0].path
        includes = [p.path for p in kwargs["includes"].items]
        op = GccCompile(source, includes)
        result = await context.execute_operation(op)
        return PathObj(result)


class GccLinkFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        assert isinstance(args[0], String)
        assert isinstance(args[1], List)
        outputname = args[0].value
        objects = [item.path for item in args[1].items]

        op = GccLink(outputname, objects)
        result = await context.execute_operation(op)
        return PathObj(result)


class GccCollectCompileCommandsFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        op = GccCollectCompileCommands()
        result = await context.execute_operation(op)
        return PathObj(result)


class ContainerizedGcc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        assert isinstance(args[0], String)

        container_image = args[0].value
        target_triplet = kwargs.get("target_triplet").value if "target_triplet" in kwargs else None

        class CompileFunc(Function):
            @override
            async def call(
                self,
                context: EvaluationContext,
                args: list[Object],
                kwargs: dict[str, Object],
            ) -> Object:
                assert isinstance(args[0], PathObj)
                assert isinstance(kwargs["includes"], List)
                source = args[0].path
                includes = [p.path for p in kwargs["includes"].items]
                op = ContainerizedGccCompile(
                    container_image, target_triplet, source, includes
                )
                result = await context.execute_operation(op)
                return PathObj(result)

        class LinkFunc(Function):
            @override
            async def call(
                self,
                context: EvaluationContext,
                args: list[Object],
                kwargs: dict[str, Object],
            ) -> Object:
                assert isinstance(args[0], String)
                assert isinstance(args[1], List)
                outputname = args[0].value
                objects = [p.path for p in args[1].items]
                op = ContainerizedGccLink(
                    container_image, target_triplet, outputname, objects
                )
                result = await context.execute_operation(op)
                return PathObj(result)

        return DictObject(
            {
                "compile": CompileFunc(),
                "link": LinkFunc(),
            }
        )

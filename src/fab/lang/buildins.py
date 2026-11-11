import glob
from copy import copy
from pathlib import Path
from typing import override

from ..model import OperationError
from ..operations import Extract, HttpArchive, HttpGet
from ..operations.containerized_gcc import (
    GccCompile as ContainerizedGccCompile,
)
from ..operations.containerized_gcc import (
    GccLink as ContainerizedGccLink,
)
from ..operations.gcc import GccCollectCompileCommands, GccCompile, GccLink
from .data import (
    EvaluationContext,
    Function,
    FunctionCallError,
    List,
    Object,
    PathObj,
    String,
)
from .evaluator import evaluate_context
from .util import DictObject, wrap_into_function_class


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


class SubpathFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:

        path_arg = args[0]
        assert isinstance(path_arg, PathObj)

        subpath_arg = args[1]
        assert isinstance(subpath_arg, String)

        path = path_arg.path / subpath_arg.value
        if not path.exists():
            raise FunctionCallError(f"Subpath {subpath_arg.value} does not exist")

        return PathObj(path)


class GlobFunc(Function):
    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:

        pattern_arg = args[0]
        paths: list[Path] = []
        for path_arg in args[1:]:
            if isinstance(path_arg, PathObj):
                paths.append(path_arg.path)
            elif isinstance(path_arg, List):
                for item in path_arg.items:
                    if not isinstance(item, PathObj):
                        raise FunctionCallError("Expected path or list of paths")
                    paths.append(item.path)

        assert isinstance(pattern_arg, String)
        pattern = pattern_arg.value

        entries = []
        for p in paths:
            for entry in glob.glob(pattern, root_dir=p, recursive=True):
                entry_path = p / entry
                entries.append(PathObj(entry_path))

        return List(entries)


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
        target_triplet = (
            kwargs.get("target_triplet").value if "target_triplet" in kwargs else None
        )

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
                    container_image,
                    target_triplet,
                    source,
                    includes,
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
                options = []
                if "options" in kwargs:
                    assert isinstance(kwargs["options"], List)
                    options = [item.value for item in kwargs["options"].items]
                op = ContainerizedGccLink(
                    container_image,
                    target_triplet,
                    outputname,
                    objects,
                    options=options,
                )
                try:
                    result = await context.execute_operation(op)
                except OperationError as e:
                    raise FunctionCallError(e.error_line, e.error_msg)
                return PathObj(result)

        return DictObject(
            {
                "compile": CompileFunc(),
                "link": LinkFunc(),
            }
        )

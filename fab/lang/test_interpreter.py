import hashlib
from pathlib import Path
from typing import override

import pytest

from ..building import Context
from ..caching import NullCache
from ..data.base import List, String
from ..data.dictobject import DictObject
from ..data.function_wrapper import WrappingFunction
from ..data.operation_wrapper import WrappingOperation
from ..util.temp_file_structure import TempFileStructure
from .interpreter import (
    EvaluationError,
    Evaluator,
    FileLookup,
    FileLookupError,
    LoadFileFunc,
    LocalFileLookup,
    evaluate_source,
)


class NullContext(Context):
    def __init__(self) -> None:
        super().__init__(
            NullCache(),
            hashlib.md5,
            None,
            None,
        )


@pytest.mark.asyncio
async def test_evaluate_variable():
    evaluator = Evaluator(NullContext())
    obj = evaluate_source(evaluator, 'y = x x = "x_str"')
    assert await obj.get_attr("y") == String("x_str")


@pytest.mark.asyncio
async def test_evaluate_variable_not_exists():
    evaluator = Evaluator(NullContext())
    with pytest.raises(EvaluationError):
        obj = evaluate_source(evaluator, "y = x")
        await obj.get_attr(("y"))


@pytest.mark.skip
@pytest.mark.asyncio
async def test_variable_conflicts_with_buildin():
    assert False


@pytest.mark.asyncio
async def test_evaluate_literal_string():
    evaluator = Evaluator(NullContext())
    obj = evaluate_source(evaluator, 'x = "x_str"')
    assert await obj.get_attr("x") == String("x_str")


@pytest.mark.asyncio
async def test_evaluate_list():
    evaluator = Evaluator(NullContext())
    obj = evaluate_source(evaluator, 'x=[a,b,"c_str"] a="a_str" b="b_str"')
    assert await obj.get_attr("x") == List(
        [
            String("a_str"),
            String("b_str"),
            String("c_str"),
        ]
    )


@pytest.mark.skip
@pytest.mark.asyncio
async def test_evaluate_list_parallel():
    # TODO: validate that list items are evaluated in parallel
    assert False


@pytest.mark.asyncio
async def test_evaluate_attribute_ref():
    evaluator = Evaluator(NullContext())
    evaluator.add_symbol("y", DictObject({"z": String("z_str")}))
    obj = evaluate_source(evaluator, "x = y.z")
    assert await obj.get_attr("x") == String("z_str")


@pytest.mark.asyncio
async def test_evaluate_attribute_ref_not_exists():
    evaluator = Evaluator(NullContext())
    evaluator.add_symbol("y", DictObject({}))
    with pytest.raises(EvaluationError):
        obj = evaluate_source(evaluator, "x = y.z")
        await obj.get_attr("x")


@pytest.mark.asyncio
async def test_evaluate_call_function():
    evaluator = Evaluator(NullContext())
    evaluator.add_symbol("y", WrappingFunction(lambda: String("y_func")))
    obj = evaluate_source(evaluator, "x = y()")
    assert await obj.get_attr("x") == String("y_func")


@pytest.mark.asyncio
async def test_evaluate_call_function_args():
    evaluator = Evaluator(NullContext())

    def f(arg1):
        assert arg1 == String("arg1")

    evaluator.add_symbol("y", WrappingFunction(f))
    obj = evaluate_source(evaluator, 'x = y("arg1")')
    await obj.get_attr("x")


@pytest.mark.asyncio
async def test_evaluate_call_function_kwargs():
    evaluator = Evaluator(NullContext())

    def f(kwarg1):
        assert kwarg1 == String("kwarg1")

    evaluator.add_symbol("y", WrappingFunction(f))
    obj = evaluate_source(evaluator, 'x = y(kwarg1="kwarg1")')
    await obj.get_attr("x")


@pytest.mark.asyncio
async def test_evaluate_call_action():
    context = NullContext()
    evaluator = Evaluator(context)

    async def f(context_: Context):
        assert context_ is context
        return String("y_func")

    evaluator.add_symbol("y", WrappingOperation(f))
    obj = evaluate_source(evaluator, "x = y()")
    assert await obj.get_attr("x") == String("y_func")


@pytest.mark.asyncio
async def test_evaluate_call_not_callable():
    evaluator = Evaluator(NullContext())
    obj = evaluate_source(evaluator, 'x = "not_callable"()')
    with pytest.raises(EvaluationError):
        await obj.get_attr("x")


@pytest.mark.skip
@pytest.mark.asyncio
async def test_evaluate_call_args_in_parallel():
    # TODO: Test that call arguments are evaluated in parallel
    assert False


@pytest.mark.skip
@pytest.mark.asyncio
async def test_evaluate_circular_dependency_detection():
    assert False


@pytest.mark.skip
@pytest.mark.asyncio
async def test_evaluated_variables_reuse():
    """Test a variable is only evaluated once, and result stored for next reference to the variable."""
    assert False


class DummyFileLookup(FileLookup):
    file_table: dict[str, str]

    def __init__(self, file_table: dict[str, str]) -> None:
        self.file_table = file_table

    @override
    def lookup(self, name: str) -> str:
        return self.file_table[name]


@pytest.mark.asyncio
async def test_load_file():
    evaluator = Evaluator(NullContext())
    file_lookup = DummyFileLookup({"test.txt": 'y="y_str"'})
    evaluator.add_symbol("load", LoadFileFunc(file_lookup, evaluator))
    obj = evaluate_source(evaluator, 'x = load("test.txt")')
    assert await (await obj.get_attr("x")).get_attr("y") == String("y_str")


def test_local_file_lookup():
    with TempFileStructure(
        [
            ("file1", "content1"),
            ("subdir1/file2", "content2"),
            ("subdir1/subdir2/file3", "content3"),
        ]
    ) as root:
        base = root / "subdir1"
        file_lookup = LocalFileLookup(base)

        assert file_lookup.lookup("file2") == "content2"
        assert file_lookup.lookup("../file1") == "content1"
        assert file_lookup.lookup("subdir2/file3") == "content3"


def test_local_file_lookup_absolute():
    file_lookup = LocalFileLookup(Path("/"))
    with pytest.raises(FileLookupError):
        file_lookup.lookup("/etc/hostname")

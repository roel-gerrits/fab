from collections.abc import Mapping
from pathlib import Path
from typing import override

import pytest

from ..model import Operation
from .data import EvaluationContext, List, Object, String
from .evaluator import EvaluationError, evaluate
from .parser import parse
from .util import BaseEvaluationContext, DictObject, SimpleFunction


class DummyEvaluationContext(BaseEvaluationContext):
    def __init__(
        self,
        initial_file: Path = Path("dummy.txt"),
        buildins: Mapping[str, Object] | None = None,
    ) -> None:
        super().__init__(initial_file, buildins or {})

    @override
    async def execute_operation(self, operation: Operation) -> None:
        raise NotImplementedError


async def evaluate_source(
    source: str,
    name: str,
    buildins: Mapping[str, Object] | None = None,
    context: EvaluationContext | None = None,
) -> Object:
    assignments = parse(source)
    target = assignments[name]
    ctx = context or DummyEvaluationContext(buildins=buildins)
    return await evaluate(target, assignments, {}, ctx)


@pytest.mark.asyncio
async def test_evaluate_variable():
    obj = await evaluate_source('y = x x = "x_str"', "x")
    assert obj == String("x_str")


@pytest.mark.asyncio
async def test_evaluate_variable_not_exists():
    with pytest.raises(EvaluationError):
        await evaluate_source("y = x", "y")


@pytest.mark.skip
@pytest.mark.asyncio
async def test_variable_conflicts_with_buildin():
    assert False


@pytest.mark.asyncio
async def test_evaluate_literal_string():
    obj = await evaluate_source('x = "x_str"', "x")
    assert obj == String("x_str")


@pytest.mark.asyncio
async def test_evaluate_list():
    obj = await evaluate_source('x=[a,b,"c_str"] a="a_str" b="b_str"', "x")
    assert obj == List(
        [
            String("a_str"),
            String("b_str"),
            String("c_str"),
        ]
    )


@pytest.mark.asyncio
async def test_evaluate_list_comprehension():
    obj = await evaluate_source('x=[x for x in ["a", "b", "c"]]', "x")
    print(obj)


@pytest.mark.skip
@pytest.mark.asyncio
async def test_evaluate_list_parallel():
    # TODO: validate that list items are evaluated in parallel
    assert False


@pytest.mark.asyncio
async def test_evaluate_attribute_ref():
    buildins = {"y": DictObject({"z": String("z_str")})}
    obj = await evaluate_source("x = y.z", "x", buildins)
    assert obj == String("z_str")


@pytest.mark.asyncio
async def test_evaluate_attribute_ref_not_exists():
    buildins = {"y": DictObject({})}
    with pytest.raises(EvaluationError):
        await evaluate_source("x = y.z", "x", buildins)


@pytest.mark.asyncio
async def test_evaluate_call_function():
    buildins = {"y": SimpleFunction(lambda: String("y_func"))}
    obj = await evaluate_source("x = y()", "x", buildins)
    assert obj == String("y_func")


@pytest.mark.asyncio
async def test_evaluate_call_function_args():

    def f(arg1):
        assert arg1 == String("arg1")
        return String("f_result")

    buildins = {"y": SimpleFunction(f)}
    obj = await evaluate_source('x = y("arg1")', "x", buildins)
    assert obj == String("f_result")


@pytest.mark.asyncio
async def test_evaluate_call_function_kwargs():
    def f(kwarg1):
        assert kwarg1 == String("arg1")
        return String("f_result")

    buildins = {"y": SimpleFunction(f)}
    obj = await evaluate_source('x = y(kwarg1="arg1")', "x", buildins)
    assert obj == String("f_result")


@pytest.mark.asyncio
async def test_evaluate_call_not_callable():
    with pytest.raises(EvaluationError):
        await evaluate_source('x = "not_callable"()', "x")


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

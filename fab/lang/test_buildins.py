from pathlib import Path

import pytest

from ..util.temp_file_structure import TempFileStructure
from .buildins import LoadFunc
from .data import String
from .evaluator import EvaluationError
from .test_evaluator import DummyEvaluationContext, evaluate_source


@pytest.mark.asyncio
async def test_load_file():
    buildins = {"load": LoadFunc()}
    with TempFileStructure(
        [
            ("test.txt", 'y = "y_str"'),
        ]
    ) as root:
        context = DummyEvaluationContext(root / "_", buildins)
        obj = await evaluate_source('x = load("test.txt").y', "x", buildins, context)
        assert obj == String("y_str")


@pytest.mark.asyncio
async def test_local_file_lookup():
    buildins = {"load": LoadFunc()}
    with TempFileStructure(
        [
            ("file1", 'y = "str_1"'),
            ("subdir1/file2", 'y = "str_2"'),
            ("subdir1/subdir2/file3", 'y = "str_3"'),
        ]
    ) as root:
        base = root / "subdir1"
        context = DummyEvaluationContext(base / "_", buildins)
        assert await evaluate_source(
            'x = load("../file1").y', "x", buildins, context
        ) == String("str_1")
        assert await evaluate_source(
            'x = load("file2").y', "x", buildins, context
        ) == String("str_2")
        assert await evaluate_source(
            'x = load("subdir2/file3").y', "x", buildins, context
        ) == String("str_3")


@pytest.mark.asyncio
async def test_local_file_lookup_absolute():
    buildins = {"load": LoadFunc()}
    context = DummyEvaluationContext(Path("_"), buildins)
    with pytest.raises(EvaluationError):
        assert await evaluate_source(
            'x = load("/absolute_file")', "x", buildins, context
        )

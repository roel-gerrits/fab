import pytest

from fab.lang.astree import SourcePosition
from .parser import parse


def test_assignment_twice():
    with pytest.raises(RuntimeError):
        parse('a = "" a=""')


def test_comments():
    assignments = parse("x=X \n # y=Y \n z=Z")
    assert assignments.keys() == {"x", "z"}


def test_list_comprehension():
    result = parse('x=[x for x in ["a", "b", "c"]]')
    print(result)


def test_ast_source_position():
    assignments = parse('xxx="xstr"')
    print(assignments)
    expr = assignments["xxx"]
    assert expr.source_position == SourcePosition(1, 5, 1, 11)

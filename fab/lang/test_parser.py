import pytest
from .parser import parse


def test_assignment_twice():
    with pytest.raises(RuntimeError):
        parse('a = "" a=""')


def test_comments():
    assignments = parse("x=X \n # y=Y \n z=Z")
    assert assignments.keys() == {"x", "z"}

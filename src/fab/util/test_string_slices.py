import pytest

from .string_slices import string_slices


def test_string_slices():
    assert string_slices("abcdefg", 2, 2) == ["ab", "cd"]


def test_string_slices_too_short():
    with pytest.raises(ValueError):
        string_slices("abc", 2, 2)

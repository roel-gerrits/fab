import hashlib

import pytest

from ..util.temp_file_structure import TempFileStructure
from ..data.base import Object, String, List, PathObj
from ..building.keybuilder import create_key_using_algo

from ..caching.abc import Key


def create_key(*objs: Object) -> Key:
    return create_key_using_algo(hashlib.sha256, objs)


def test_string():
    obj1 = String("hello world")
    obj2 = String("hello world")
    obj3 = String("hello WORLD")
    assert create_key(obj1) == create_key(obj2)
    assert create_key(obj1) != create_key(obj3)


def test_list():
    obj1 = List([String("hello"), String("world")])
    obj2 = List([String("hello"), String("world")])
    obj3 = List([String("hello"), String("WORLD")])
    assert create_key(obj1) == create_key(obj2)
    assert create_key(obj1) != create_key(obj3)

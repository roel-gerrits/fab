from collections.abc import Iterable, Sequence
import pathlib

from ..caching import HashAlgo, Key
from ..data.base import Object, String, List, PathObj
from .context import Context
from fab.data import base
from ..util.hash_path import chunkify_path


def create_key(context: Context, items: Sequence[Object|bytes]) -> Key:
    return create_key_using_algo(context.hash_algo, items)


def create_key_using_algo(algo: HashAlgo, objs: Sequence[Object|bytes]) -> Key:
    digest = algo()

    for chunk in chunkify_objects(objs):
        digest.update(chunk)

    return Key(digest.digest())


def chunkify_objects(objs: Sequence[Object|bytes]) -> Iterable[bytes]:
    for obj in objs:
        if isinstance(obj, bytes):
            yield obj
        elif isinstance(obj, String):
            yield obj.value.encode()
        elif isinstance(obj, List):
            yield from chunkify_objects(obj.items)
        elif isinstance(obj, PathObj):
            yield from chunkify_path(obj.path)
        else:
            raise NotImplementedError(f"Unsupported object type: {type(obj).__name__}")



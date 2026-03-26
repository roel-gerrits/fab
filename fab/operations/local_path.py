from ..data.function_wrapper import WrappingFunction
from ..data.base import String, PathObj
from pathlib import Path


def _local_path(path_str: String) -> PathObj:
    path = Path.cwd() / path_str.value
    if not path.exists():
        raise RuntimeError("Local path does not exist")

    return PathObj(path)


local_path = WrappingFunction(_local_path)

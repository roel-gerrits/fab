from typing import Any


def flatten(lst: list[Any]) -> list[Any]:
    result: list[Any] = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result

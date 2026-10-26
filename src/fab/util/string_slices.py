from collections.abc import Sequence


def string_slices(inp: str, *slices: int) -> Sequence[str]:
    """Splits the input string into slices based on the provided slice positions."""
    if not slices:
        return []

    current_pos = 0
    result: list[str] = []
    for size in slices:
        if current_pos + size > len(inp):
            raise ValueError("Slice sizes exceed input string length.")
        
        result.append(inp[current_pos:current_pos + size])
        current_pos += size

    return result

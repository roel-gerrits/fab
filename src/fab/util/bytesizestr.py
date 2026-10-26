import re

__steps = [
    (1024**0, "B"),
    (1024**1, "KiB"),
    (1024**2, "MiB"),
    (1024**3, "GiB"),
    (1024**4, "TiB"),
    (1024**5, "PiB"),
]


def bytesize2str(size: int) -> str:
    for step_size, suffix in __steps:
        limit = step_size * 1024
        if size < limit:
            return f"{size / step_size:.1f} {suffix}"
    return "huge!"


__suffixes = {
    "K": 1024**1,
    "M": 1024**2,
    "G": 1024**3,
    "T": 1024**4,
    "P": 1024**5,
}


def str2bytesize(size: str) -> int:
    match = re.match(r"(\d+(?:\.\d+)?)(\w?)", size)
    if not match:
        raise ValueError(f"Could not convert '{size}' to bytes")

    value = float(match.group(1))
    suffix = match.group(2).upper()

    try:
        return int(value * __suffixes[suffix])
    except KeyError:
        raise ValueError(f"Unknown suffix '{suffix}'")

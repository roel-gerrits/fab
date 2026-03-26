from pathlib import Path
from collections.abc import Iterable


def chunkify_path(base_path: Path) -> Iterable[bytes]:

    if not base_path.exists():
        raise RuntimeError(f"Path does not exist: {base_path}")

    def visit_entry(path: Path) -> Iterable[bytes]:
        subpath = path.relative_to(base_path.parent)
        yield str(subpath).encode()
        if path.is_file():
            yield path.read_bytes()
        elif path.is_dir():
            for child in sorted(path.iterdir()):
                yield from visit_entry(child)
        else:
            raise NotImplementedError(f"Unsupported path type: {path}")

    yield from visit_entry(base_path)


def hash_path(hash_func, path: Path) -> bytes:
    for chunk in chunkify_path(path):
        hash_func.update(chunk)
    return hash_func.digest()

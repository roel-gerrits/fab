from collections.abc import Sequence
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp


class TempFileStructure:
    def __init__(self, entries: Sequence[tuple[str, str | None]]) -> None:
        self.__root = Path(mkdtemp())
        for path, content in entries:
            fullpath = self.__root / path
            # print(fullpath)
            if path.endswith("/"):
                fullpath.mkdir(parents=True, exist_ok=True)
            elif content:
                fullpath.parent.mkdir(parents=True, exist_ok=True)
                fullpath.touch()
                fullpath.write_text(content)

    def __enter__(self) -> Path:
        return self.__root

    def __exit__(self, *exc_info):
        rmtree(self.__root)
        pass

from pathlib import Path
from tempfile import mkdtemp


class SandboxFactory:
    def __init__(self, root: Path):
        self.__root = root
        self.__root.mkdir(parents=True, exist_ok=True)

    def create(self) -> Path:
        path = Path(mkdtemp(dir=self.__root))
        return path

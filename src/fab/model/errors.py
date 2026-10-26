from .outputchunks import OutputChunk


class Error(RuntimeError):
    pass


class CommandFailedError(Error):
    cmd: list[str]
    exitcode: int
    output: list[OutputChunk]

    def __init__(
        self, cmd: list[str], exitcode: int, output: list[OutputChunk]
    ) -> None:
        self.cmd = cmd
        self.exitcode = exitcode
        self.output = output
        super().__init__(f"Command failed with exitcode {self.exitcode}")

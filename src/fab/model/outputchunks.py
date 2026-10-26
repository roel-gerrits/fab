from dataclasses import dataclass

import enum


class StreamType(enum.Enum):
    STDOUT = enum.auto()
    STDERR = enum.auto()


@dataclass
class OutputChunk:
    type: StreamType
    chunk: bytes

import random
from datetime import datetime, timedelta
from pathlib import Path

from .diskcache import Log

ONE_HOUR = timedelta(hours=1)


def random_key() -> bytes:
    return random.randbytes(16)


def test_empty(tmp_path: Path):
    log = Log(tmp_path / "log.log")
    assert list(log.read_new_to_old()) == []


def test_read(tmp_path: Path):

    t0 = datetime(2000, 1, 1, 0, 0, 0)
    t1 = t0 + ONE_HOUR
    t2 = t1 + ONE_HOUR

    k0 = random_key()
    k1 = random_key()
    k2 = random_key()

    log1 = Log(tmp_path / "log.log")
    log1.write(t0, k0)
    log1.write(t1, k1)
    log1.write(t2, k2)

    log2 = Log(tmp_path / "log.log")

    gen = log2.read_new_to_old()
    assert next(gen) == (t2, k2)
    assert next(gen) == (t1, k1)
    assert next(gen) == (t0, k0)

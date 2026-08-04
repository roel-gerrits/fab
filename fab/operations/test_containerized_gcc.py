from pathlib import Path
from .containerized_gcc import _parse_make_deps


def test_parse_make_deps():
    assert list(_parse_make_deps(
        "main.o: main.cpp lib1.h lib2.h \\\n lib3.h lib4.h \\\n lib5.h path\\ with\\ spaces.h"
    )) == [
        Path("lib1.h"),
        Path("lib2.h"),
        Path("lib3.h"),
        Path("lib4.h"),
        Path("lib5.h"),
        Path("path with spaces.h"),
    ]

from .temp_file_structure import TempFileStructure
from .hash_path import hash_path
from pathlib import Path
import hashlib
import pytest

def path_key(path: Path) -> str:
    hashfunc = hashlib.sha256()
    return hash_path(hashfunc, path).hex()

def test_path():
    with TempFileStructure(
        [
            ("file1", "file1"),
            ("file2", "file2"),
        ]
    ) as root:
        obj1 = Path(root / "file1")
        obj2 = Path(root / "file1")
        obj3 = Path(root / "file2")
        assert path_key(obj1) == path_key(obj2)
        assert path_key(obj1) != path_key(obj3)


def test_path_complex():
    with TempFileStructure(
        [
            ("dir1/file1", "file1"),
            ("dir1/file2", "file2"),
            ("dir2/file3", "file3"),
            ("dir2/file4", "file4"),
        ]
    ) as root:
        obj1 = Path(root / "dir1")
        obj2 = Path(root / "dir1")
        obj3 = Path(root / "dir2")
        assert path_key(obj1) == path_key(obj2)
        assert path_key(obj1) != path_key(obj3)


def test_path_filenames():
    """Test that flenames are included in the key as well, not just file contents."""

    with TempFileStructure(
        [
            ("file1", "fileX"),
            ("file2", "fileX"),
        ]
    ) as root:
        obj1 = Path(root / "file1")
        obj2 = Path(root / "file2")
        assert path_key(obj1) != path_key(obj2)


def test_filenames_with_respect_to_base():
    """Test that filenames are included with respect to the base directory, not absolute."""

    tfs1 = TempFileStructure(
        [
            ("dir1/file1", "fileX"),
        ]
    )
    tfs2 = TempFileStructure(
        [
            ("dir1/file1", "fileX"),
        ]
    )

    with tfs1 as root1, tfs2 as root2:
        obj1 = Path(root1 / "dir1")
        obj2 = Path(root2 / "dir1")
        assert path_key(obj1) == path_key(obj2)


def test_dirnames_with_respect_to_base():
    """Test that full paths are included in the key with respect to the base directory."""

    tfs1 = TempFileStructure(
        [
            ("dir1/file1", "fileX"),
        ]
    )
    tfs2 = TempFileStructure(
        [
            ("dir2/file1", "fileX"),
        ]
    )

    with tfs1 as root1, tfs2 as root2:
        obj1 = Path(root1)
        obj2 = Path(root2)
        assert path_key(obj1) != path_key(obj2)


def test_order_insensitivity_for_paths():
    """Test that the order of files in a directory does not affect the key."""
    tfs1 = TempFileStructure(
        [
            ("base/file1", "fileX"),
            ("base/file2", "fileY"),
        ]
    )
    tfs2 = TempFileStructure(
        [
            ("base/file2", "fileY"),
            ("base/file1", "fileX"),
        ]
    )

    with tfs1 as root1, tfs2 as root2:
        obj1 = Path(root1 / "base")
        obj2 = Path(root2 / "base")
        assert path_key(obj1) == path_key(obj2)


@pytest.mark.skip
def test_execution_bit():
    """Test that exeuction bit is the only bit that affects the key for files."""
    assert False
    pass

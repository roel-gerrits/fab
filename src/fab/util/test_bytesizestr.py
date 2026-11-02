from .bytesizestr import str2bytesize


def test_str2bytesize():
    assert str2bytesize("0") == 0

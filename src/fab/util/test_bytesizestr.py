from .bytesizestr import bytesize2str, str2bytesize


def test_str2bytesize():
    assert str2bytesize("0") == 0

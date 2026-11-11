from hashlib import sha256
from pathlib import Path
from threading import Event, Thread

import pytest

from basepack.memory.images import ImageSource, retain_image


def image_source():
    data = b"image evidence" * 1024
    return ImageSource("scan.PNG", sha256(data).hexdigest(), len(data), 0, data)


def test_concurrent_retention_never_exposes_an_incomplete_snapshot(tmp_path, monkeypatch):
    source = image_source()
    assets = tmp_path / "assets"
    target = assets / (source.revision + ".png")
    started, release = Event(), Event()
    failures, results = [], []

    def interrupted_write(path, data):
        with path.open("wb") as stream:
            middle = len(data) // 2
            stream.write(data[:middle])
            stream.flush()
            if not started.is_set():
                started.set()
                assert release.wait(10)
            stream.write(data[middle:])
        return len(data)

    monkeypatch.setattr(Path, "write_bytes", interrupted_write)

    def retain():
        try:
            results.append(retain_image(tmp_path, source))
        except Exception as error:
            failures.append(error)

    first = Thread(target=retain)
    first.start()
    try:
        assert started.wait(10)
        exposed_incomplete = target.exists()
        retain()
    finally:
        release.set()
        first.join(10)
    assert not first.is_alive()
    assert failures == []
    assert exposed_incomplete is False
    assert results == ["assets/" + target.name] * 2
    assert target.read_bytes() == source.data
    assert list(assets.iterdir()) == [target]


def test_existing_corrupt_snapshot_is_not_replaced(tmp_path):
    source = image_source()
    target = tmp_path / "assets" / (source.revision + ".png")
    target.parent.mkdir()
    target.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Image evidence snapshot revision mismatch"):
        retain_image(tmp_path, source)
    assert target.read_bytes() == b"corrupt"
    assert list(target.parent.iterdir()) == [target]


@pytest.mark.parametrize("failure", ["write", "hash", "publish"])
def test_failed_retention_removes_its_temporary_file(tmp_path, monkeypatch, failure):
    source = image_source()
    write_bytes = Path.write_bytes

    def failed_write(path, data):
        write_bytes(path, data[:len(data) // 2])
        if failure == "write":
            raise OSError("write failed")
        return len(data) // 2

    def failed_replace(path, target):
        raise OSError("publish failed")

    if failure == "publish":
        monkeypatch.setattr(Path, "replace", failed_replace)
    else:
        monkeypatch.setattr(Path, "write_bytes", failed_write)
    expected_error = ValueError if failure == "hash" else OSError
    with pytest.raises(expected_error):
        retain_image(tmp_path, source)
    assert list((tmp_path / "assets").iterdir()) == []

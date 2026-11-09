"""Version original image bytes and retain portable, content-addressed evidence."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


@dataclass(frozen=True)
class ImageSource:
    path: str
    revision: str
    size: int
    mtime_ns: int
    data: bytes


def read_image(root: Path, path: str) -> ImageSource:
    target = (root / path).resolve()
    if Path(path).is_absolute() or not target.is_relative_to(root):
        raise ValueError(f"Image path must stay within project: {path}")
    before = target.stat()
    data = target.read_bytes()
    after = target.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f"Image changed while reading: {path}")
    return ImageSource(target.relative_to(root).as_posix(), sha256(data).hexdigest(),
                       after.st_size, after.st_mtime_ns, data)


def retain_image(memory_dir: Path, source: ImageSource) -> str:
    relative = Path("assets") / (source.revision + Path(source.path).suffix.lower())
    target = memory_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(source.data)
    if sha256(target.read_bytes()).hexdigest() != source.revision:
        raise ValueError(f"Image evidence snapshot revision mismatch: {target}")
    return relative.as_posix()

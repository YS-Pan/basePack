"""Task-scoped stop and publication arbitration shared by host and worker."""

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import time


class MaintenanceStopped(RuntimeError):
    pass


@contextmanager
def _locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as file:
        deadline = time.monotonic() + 0.5
        while True:
            try:
                file.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'Maintenance control is busy: {path}')
                time.sleep(0.01)
        try:
            yield file
        finally:
            file.seek(0)
            if os.name == 'nt':
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(file, fcntl.LOCK_UN)


def stop(path):
    """Stop this task's future work without waiting for active encoding or commit."""
    with _locked(path) as file:
        file.seek(0)
        file.write(b'S')
        file.flush()


def begin_commit(path):
    """Claim commit under the stop lock; a later stop leaves this commit alone."""
    with _locked(path) as file:
        file.seek(0)
        if file.read(1) == b'S':
            raise MaintenanceStopped('Maintenance stopped before publication')


def check(path):
    begin_commit(path)

"""Run SurrealDB in a private Windows console for graceful shutdown."""

from collections.abc import Mapping, Sequence
import ctypes
import os
import signal
import subprocess
import sys
from typing import IO


class SurrealProcess(subprocess.Popen[bytes]):
    def __init__(self, argv: Sequence[str], *, env: Mapping[str, str], log: IO[str]) -> None:
        self._log = log
        super().__init__(
            argv, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    def stop(self) -> None:
        """Send one Ctrl-Break to the ready child and wait for its successful exit."""
        if self.poll() is None:
            # AttachConsole changes process-wide state. Use a detached sender so the launcher
            # keeps its own console, and target only the child's process group.
            subprocess.run(
                [sys.executable, "-I", "-B", "-X", "utf8", __file__, str(self.pid)],
                stdin=subprocess.DEVNULL, stdout=self._log, stderr=subprocess.STDOUT,
                creationflags=subprocess.DETACHED_PROCESS, check=True, timeout=10,
            )
        status = self.wait(timeout=30)
        if status:
            raise subprocess.CalledProcessError(status, self.args)


def launch_surreal(argv: Sequence[str], *, env: Mapping[str, str], log: IO[str]) -> SurrealProcess:
    return SurrealProcess(argv, env=env, log=log)


def _send_console_break(pid: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    if not kernel.AttachConsole(pid):
        raise ctypes.WinError(ctypes.get_last_error())
    os.kill(pid, signal.CTRL_BREAK_EVENT)


if __name__ == "__main__":
    _send_console_break(int(sys.argv[1]))

"""Observe local process families without owning Condor job processes."""

import os


def _descendants(roots: set[int], parents: dict[int, int]) -> set[int]:
    found = set(roots)
    while True:
        children = {pid for pid, parent in parents.items() if parent in found}
        if children <= found:
            return found
        found.update(children)


def _process_parents() -> dict[int, int]:
    """Toolhelp lists PIDs and parent PIDs without opening another user's process."""
    if os.name != "nt":
        import psutil
        return {process.pid: process.ppid() for process in psutil.process_iter()}
    import ctypes
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ("Process32FirstW", "Process32NextW"):
        function = getattr(kernel, name)
        function.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
        function.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    parents = {}
    entry = ProcessEntry(dwSize=ctypes.sizeof(ProcessEntry))
    try:
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            parents[entry.th32ProcessID] = entry.th32ParentProcessID
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(snapshot)
    return parents

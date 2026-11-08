"""Supervisor ownership of its model process, adapted from the old Qwen bridge."""
import ctypes
from ctypes import wintypes
import os


def process_alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.OpenProcess(0x100000, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:  # ERROR_INVALID_PARAMETER: no such process.
            return False
        raise ctypes.WinError(error)
    try:
        return api.WaitForSingleObject(handle, 0) == 0x102  # WAIT_TIMEOUT
    finally:
        api.CloseHandle(handle)


class WorkerProcessOwner:
    def __init__(self, process):
        self.handle = None
        if os.name != "nt":
            return

        class Basic(ctypes.Structure):
            _fields_ = [("ProcessTime", ctypes.c_longlong), ("JobTime", ctypes.c_longlong),
                ("Flags", wintypes.DWORD), ("MinimumWorkingSet", ctypes.c_size_t),
                ("MaximumWorkingSet", ctypes.c_size_t), ("ActiveProcesses", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("Priority", wintypes.DWORD), ("Scheduling", wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                        ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]

        class Extended(ctypes.Structure):
            _fields_ = [("Basic", Basic), ("IO", IO), ("ProcessLimit", ctypes.c_size_t),
                ("JobLimit", ctypes.c_size_t), ("PeakProcess", ctypes.c_size_t), ("PeakJob", ctypes.c_size_t)]

        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        api.CreateJobObjectW.restype = wintypes.HANDLE
        api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        api.SetInformationJobObject.restype = wintypes.BOOL
        api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        api.AssignProcessToJobObject.restype = wintypes.BOOL
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        api.CloseHandle.restype = wintypes.BOOL
        handle = api.CreateJobObjectW(None, None)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = Extended()
        limits.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not api.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not api.AssignProcessToJobObject(handle, wintypes.HANDLE(int(process._handle))):
            error = ctypes.get_last_error()
            api.CloseHandle(handle)
            raise ctypes.WinError(error)
        self.api, self.handle = api, handle

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None

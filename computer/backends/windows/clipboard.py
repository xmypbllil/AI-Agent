"""Windows clipboard text driver."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass

from computer.backends.windows.user32 import kernel32, raise_last_error, user32

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


@dataclass(frozen=True, slots=True)
class WindowsClipboardDriver:
    def read(self) -> str:
        if not user32.OpenClipboard(None):
            raise_last_error("OpenClipboard failed")
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                raise_last_error("GlobalLock failed")
            try:
                return ctypes.wstring_at(pointer)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()

    def write(self, text: str) -> None:
        encoded_size = (len(text) + 1) * ctypes.sizeof(ctypes.c_wchar)
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, encoded_size)
        if not handle:
            raise_last_error("GlobalAlloc failed")
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise_last_error("GlobalLock failed")
        ctypes.memmove(pointer, ctypes.create_unicode_buffer(text), encoded_size)
        kernel32.GlobalUnlock(handle)

        if not user32.OpenClipboard(None):
            raise_last_error("OpenClipboard failed")
        try:
            user32.EmptyClipboard()
            if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                raise_last_error("SetClipboardData failed")
        finally:
            user32.CloseClipboard()

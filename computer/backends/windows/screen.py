"""Windows screen capture driver."""

from __future__ import annotations

import ctypes
import struct
from dataclasses import dataclass

from computer.backends.windows.user32 import BITMAPINFO, gdi32, raise_last_error, user32
from computer.models import Rect

SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0


@dataclass(frozen=True, slots=True)
class WindowsScreenDriver:
    def capture(self, region: Rect | None = None) -> bytes:
        left = 0 if region is None else region.left
        top = 0 if region is None else region.top
        width = user32.GetSystemMetrics(0) if region is None else region.width
        height = user32.GetSystemMetrics(1) if region is None else region.height

        screen_dc = user32.GetDC(None)
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
        if not bitmap:
            raise_last_error("CreateCompatibleBitmap failed")
        gdi32.SelectObject(memory_dc, bitmap)
        if not gdi32.BitBlt(memory_dc, 0, 0, width, height, screen_dc, left, top, SRCCOPY):
            raise_last_error("BitBlt failed")

        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(info.bmiHeader)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = BI_RGB

        pixel_count = width * height
        buffer = ctypes.create_string_buffer(pixel_count * 4)
        copied = gdi32.GetDIBits(
            memory_dc,
            bitmap,
            0,
            height,
            buffer,
            ctypes.byref(info),
            DIB_RGB_COLORS,
        )
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)
        if copied == 0:
            raise_last_error("GetDIBits failed")
        return self._bmp_bytes(width, height, buffer.raw)

    def _bmp_bytes(self, width: int, height: int, pixels: bytes) -> bytes:
        header_size = 14 + 40
        image_size = len(pixels)
        file_size = header_size + image_size
        file_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, header_size)
        dib_header = struct.pack(
            "<IIIHHIIIIII",
            40,
            width,
            height,
            1,
            32,
            BI_RGB,
            image_size,
            0,
            0,
            0,
            0,
        )
        return file_header + dib_header + pixels

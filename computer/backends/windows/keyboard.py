"""Windows keyboard driver."""

from __future__ import annotations

from dataclasses import dataclass

from computer.backends.windows.user32 import raise_last_error, user32

KEYEVENTF_KEYUP = 0x0002
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_TAB = 0x09
VK_SPACE = 0x20
VK_BACK = 0x08

KEYS = {
    "enter": VK_RETURN,
    "escape": VK_ESCAPE,
    "esc": VK_ESCAPE,
    "tab": VK_TAB,
    "space": VK_SPACE,
    "backspace": VK_BACK,
}


@dataclass(frozen=True, slots=True)
class WindowsKeyboardDriver:
    def write(self, text: str) -> None:
        for char in text:
            code = ord(char)
            if user32.VkKeyScanW(code) == -1:
                self._send_unicode(char)
                continue
            user32.keybd_event(code, 0, 0, 0)
            user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)

    def press(self, key: str) -> None:
        normalized = key.lower()
        virtual_key = KEYS.get(normalized)
        if virtual_key is None and len(key) == 1:
            virtual_key = ord(key.upper())
        if virtual_key is None:
            raise ValueError(f"Unsupported key: {key}")
        user32.keybd_event(virtual_key, 0, 0, 0)
        user32.keybd_event(virtual_key, 0, KEYEVENTF_KEYUP, 0)

    def _send_unicode(self, char: str) -> None:
        if not user32.SendMessageW(user32.GetForegroundWindow(), 0x0102, ord(char), 0):
            raise_last_error("SendMessageW failed")

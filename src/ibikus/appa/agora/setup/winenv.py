"""Persistent per-user environment variables on Windows (no administrator rights needed)."""

from __future__ import annotations

import sys
from collections.abc import Mapping


def set_user_env(values: Mapping[str, str]) -> None:
    """Write HKCU\\Environment values and notify running programs (Explorer, Ollama's tray
    app on restart) that the environment changed."""
    if sys.platform != "win32":
        raise NotImplementedError("user environment variables are only managed on Windows")
    import ctypes
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        for name, value in values.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    hwnd_broadcast, wm_settingchange, smto_abortifhung = 0xFFFF, 0x001A, 0x0002
    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        hwnd_broadcast,
        wm_settingchange,
        0,
        "Environment",
        smto_abortifhung,
        5000,
        ctypes.byref(result),
    )
